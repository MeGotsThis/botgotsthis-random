import random
import re
from collections import defaultdict
from datetime import datetime, timedelta  # noqa: F401
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Match  # noqa: F401,E501
from typing import Optional, Sequence, Set  # noqa: F401

import aiohttp

import bot
from lib.api import twitch
from lib.cache import CacheStore
from lib.data import ChatCommandArgs
from lib.data.message import Message
from lib.helper import parser
from lib.helper.chat import not_feature, permission, permission_not_feature

from .library import number


async def logLastMessage(args: ChatCommandArgs) -> bool:
    if 'lastMessage' not in args.chat.sessionData:
        sessionData: Dict[Any, Any] = args.chat.sessionData
        sessionData['lastMessage'] = defaultdict(lambda: datetime.min)
    args.chat.sessionData['lastMessage'][args.nick] = args.timestamp
    return False


@permission_not_feature(('broadcaster', None),
                        ('moderator', 'winnerbroadcaster'))
async def commandWinner(args: ChatCommandArgs) -> bool:
    args.chat.send('The winning user is...')

    url = f'http://tmi.twitch.tv/group/user/{args.chat.channel}/chatters'
    session: aiohttp.ClientSession
    response: aiohttp.ClientResponse
    users: Set[str]
    async with aiohttp.ClientSession() as session, \
            session.get(url, timeout=bot.config.httpTimeout) as response:
        if response.status // 100 in [4, 5]:
            users = set(args.chat.ircUsers)
        else:
            usersFromTwitch: Dict[str, Any] = await response.json()
            users = set(usersFromTwitch['chatters']['viewers'])
            users |= set(usersFromTwitch['chatters']['moderators'])
            users |= set(usersFromTwitch['chatters']['global_mods'])
            users |= set(usersFromTwitch['chatters']['admins'])
            users |= set(usersFromTwitch['chatters']['staff'])
            if not users:
                users = set(args.chat.ircUsers)

    if not users:
        args.chat.send('nobody! Twitch, why do you error!')
        return False

    noLurk: Optional[str] = await args.data.getChatProperty(
        args.chat.channel, 'winnerNoLurk')
    user: str
    if noLurk is not None:
        earliest: datetime = args.timestamp - timedelta(seconds=int(noLurk))
        for user in set(users):
            user = user.lower()
            if user == bot.config.botnick:
                continue
            sessionData: Dict[Any, Any] = args.chat.sessionData
            if ('lastMessage' in sessionData
                    and sessionData['lastMessage'][user] < earliest):
                users.discard(user)

    user = random.choice(list(users))

    data: Optional[Dict[str, Any]]
    try:
        response, data = await twitch.get_call(
            args.chat.channel,
            f'/kraken/users/{user}/follows/channels/{args.chat.channel}',
            headers={
                'Accept': 'application/vnd.twitchtv.v3+json',
                })
        if user == args.chat.channel:
            args.chat.send(f'{user}! PogChamp Streamer has won !winner')
        elif response.status == 404:
            args.chat.send(f'{user}! (user does not follow this stream)')
        else:
            args.chat.send(f'{user}!')
    except aiohttp.ClientResponseError as e:
        if e.code != 404:
            raise
        args.chat.send(f'{user}! (user does not follow this stream)')
    return True


@permission('broadcaster')
async def commandSetNoLurk(args: ChatCommandArgs) -> bool:
    match: Optional[Match[str]] = None
    if len(args.message) > 1:
        pattern = (r"(?!$)(?:(\d{1,})w)?(?:(\d{1,})d)?"
                   r"(?:(\d{1,})h)?(?:(\d{1,})m)?(?:(\d{1,})s)?(?<!^)")
        match = re.fullmatch(pattern, args.message.lower[1])
    if match:
        groups: Sequence[str] = match.groups()
        duration: int = 0
        if groups[0]:
            duration += int(groups[0]) * 604800
        if groups[1]:
            duration += int(groups[1]) * 86400
        if groups[2]:
            duration += int(groups[2]) * 3600
        if groups[3]:
            duration += int(groups[3]) * 60
        if groups[4]:
            duration += int(groups[4])
            await args.data.setChatProperty(
                args.chat.channel, 'winnerNoLurk', str(duration))
        args.chat.send(f'''\
The !winner command will pick users who chatted in the last {duration} seconds\
''')
    else:
        await args.data.setChatProperty(args.chat.channel, 'winnerNoLurk')
        args.chat.send('Allowed all users for !winner')
    return True


@not_feature('noroll')
@permission('moderator')
async def commandRoll(args: ChatCommandArgs) -> bool:
    RollFunction = Callable[[Message, CacheStore], Awaitable[Optional[str]]]
    rollFunctions: List[RollFunction] = []

    if await args.data.hasFeature(args.chat.channel, 'roll.exe'):
        rollFunctions += [rollExe]
    if await args.data.hasFeature(args.chat.channel, 'roll.emote'):
        rollFunctions += [rollEmote]

    rollFunctions += [
        rollHexadecimal,
        rollBinary,
        rollInteger,
        rollFloat,
        rollComplex,
        ]
    rollFunc: RollFunction
    for rollFunc in rollFunctions:
        value: Optional[str] = await rollFunc(args.message, args.data)
        if value is not None:
            args.chat.send(f'The roll returns {value}!')
            return True
    args.chat.send('The roll returns Kappa !')
    return True


async def rollExe(message: Message, data: CacheStore) -> Optional[str]:
    if len(message) >= 2 and message.lower[1] == 'exe':
        return 'http://i.imgur.com/CFyCRkP.jpg '
    return None


async def rollHexadecimal(message: Message, data: CacheStore) -> Optional[str]:
    pattern: str = r'^(0[xX]|\$)([0-9a-fA-F]+)$'
    minInt: Optional[int] = None
    maxInt: Optional[int] = None
    prefix: Optional[str] = None
    numLen: Optional[int] = None
    if len(message) < 2:
        return None
    elif len(message) == 2:
        match = re.match(pattern, message[1])
        if match is not None:
            minInt = 0
            maxInt = int(match.group(2), 16)
            prefix = str(match.group(1))
            numLen = len(match.group(2))
        else:
            return None
    elif len(message) > 2:
        minMatch = re.match(pattern, message[1])
        maxMatch = re.match(pattern, message[2])
        if minMatch is not None and maxMatch is not None:
            minInt = int(minMatch.group(2), 16)
            maxInt = int(maxMatch.group(2), 16)
            prefix = str(minMatch.group(1))
            numLen = len(maxMatch.group(2))
        else:
            return None
    if minInt is None and maxInt is None and numLen is None and prefix is None:
        return None
    if minInt > maxInt:
        return None
    elif minInt == maxInt:
        return prefix + number.positiveBaseStr(minInt, 16).rjust(numLen, '0')
    else:
        i = int(random.randint(minInt, maxInt))
        return prefix + number.positiveBaseStr(i, 16).rjust(numLen, '0')


async def rollBinary(message: Message, data: CacheStore) -> Optional[str]:
    pattern: str = r'^(0[bB]|%)([01]+)$'
    minInt: Optional[int] = None
    maxInt: Optional[int] = None
    prefix: Optional[str] = None
    numLen: Optional[int] = None
    if len(message) < 2:
        return None
    elif len(message) == 2:
        match: Match[str] = re.match(pattern, message[1])
        if match is not None:
            minInt = 0
            maxInt = int(match.group(2), 2)
            prefix = str(match.group(1))
            numLen = len(match.group(2))
        else:
            return None
    elif len(message) > 2:
        minMatch = re.match(pattern, message[1])
        maxMatch = re.match(pattern, message[2])
        if minMatch is not None and maxMatch is not None:
            minInt = int(minMatch.group(2), 2)
            maxInt = int(maxMatch.group(2), 2)
            prefix = str(minMatch.group(1))
            numLen = len(maxMatch.group(2))
        else:
            return None
    if minInt is None and maxInt is None and numLen is None and prefix is None:
        return None
    if minInt > maxInt:
        return None
    elif minInt == maxInt:
        return prefix + number.positiveBaseStr(minInt, 2).rjust(numLen, '0')
    else:
        i = int(random.randint(minInt, maxInt))
        return prefix + number.positiveBaseStr(i, 2).rjust(numLen, '0')


async def rollInteger(message: Message, data: CacheStore) -> Optional[str]:
    try:
        minInt: int = 1
        maxInt: int = 6
        if len(message) == 1:
            pass
        elif len(message) == 2:
            maxInt = int(message[1])
        elif len(message) > 2:
            minInt = int(message[1])
            maxInt = int(message[2])

        if minInt > maxInt:
            return None
        elif minInt == maxInt:
            return str(minInt)
        else:
            return str(random.randint(minInt, maxInt))
    except Exception:
        return None


async def rollFloat(message: Message, data: CacheStore) -> Optional[str]:
    try:
        minFloat: float = 0.0
        maxFloat: float = 1.0
        if len(message) == 2:
            if message.lower[1] in ['float', 'double']:
                pass
            else:
                maxFloat = float(message[1])
        elif len(message) > 2:
            minFloat = float(message[1])
            maxFloat = float(message[2])

        return str(random.uniform(minFloat, maxFloat))
    except Exception:
        return None


async def rollComplex(message: Message, data: CacheStore) -> Optional[str]:
    try:
        complex1: complex = 0.0 + 0.0j
        complex2: complex = 1.0 + 1.0j
        if len(message) == 2:
            if message[1] in ['complex', 'imaginary']:
                pass
            else:
                complex2 = complex(message[1].replace('i', 'j'))
        elif len(message) > 2:
            complex1 = complex(message[1].replace('i', 'j'))
            complex2 = complex(message[2].replace('i', 'j'))

        r = random.uniform(complex1.real, complex2.real)
        i = random.uniform(complex1.imag, complex2.imag)
        c = str(complex(r, i))
        for item in {'j': 'i', '(': '', ')': ''}.items():
            c = c.replace(item[0], item[1])

        return c
    except Exception:
        return None


async def rollEmote(message: Message, data: CacheStore) -> Optional[str]:
    if len(message) >= 2 and message.lower[1] == 'emote':
        num = 1
        if len(message) >= 3:
            try:
                num = int(message[2])
            except Exception:
                pass
        emoteSets: Optional[Set[int]] = await data.twitch_get_bot_emote_set()
        if emoteSets is None:
            return None
        if not await data.twitch_load_emotes(emoteSets):
            return None
        emotes: Optional[Dict[int, str]] = await data.twitch_get_emotes()
        if emotes is None:
            return None
        emoteIds: List[int] = list(emotes.keys())
        randomEmotes: Iterable[str]
        randomEmotes = (emotes[random.choice(emoteIds)] for i in range(num))
        return ' '.join(randomEmotes) + ' '
    return None


@not_feature('noroll')
@permission('moderator')
async def commandRollBase(args: ChatCommandArgs) -> bool:
    full: bool = False
    if 'full' in args.message.lower:
        full = True

    b: List[str] = args.message.command.split('roll-', 1)
    base: Optional[str] = None if len(b) < 2 else str(b[1])

    minInt: int
    maxInt: int
    msg: str
    i: int
    if base is not None and base == 't':
        try:
            minInt = -121
            maxInt = 121
            if len(args.message) == 1:
                pass
            elif len(args.message) == 2:
                minInt = 0
                maxInt = number.balancedBaseInt(args.message[1])
            elif len(args.message) > 2:
                minInt = number.balancedBaseInt(args.message[1])
                maxInt = number.balancedBaseInt(args.message[2])

            if minInt > maxInt:
                minInt, maxInt = maxInt, minInt

            if minInt == maxInt:
                msg = f'The roll returns {number.balancedBaseStr(minInt)}!'
                if full:
                    msg += f' Value (base 10): {minInt}'
                args.chat.send(msg)
                return True
            else:
                i = int(random.randint(minInt, maxInt))
                msg = f'The roll returns {number.balancedBaseStr(i)}!'
                if full:
                    msg += f''' \
Value (base 10): {i};  Min (base 10): {minInt}; Max (base 10): {maxInt}'''
                args.chat.send(msg)
                return True
        except Exception:
            pass
    elif base == '!':
        try:
            minInt = 0
            maxInt = 119
            if len(args.message) == 1:
                pass
            elif len(args.message) == 2:
                minInt = 0
                maxInt = number.factorialBaseInt(args.message[1])
            elif len(args.message) > 2:
                minInt = number.factorialBaseInt(args.message[1])
                maxInt = number.factorialBaseInt(args.message[2])

            if minInt > maxInt:
                minInt, maxInt = maxInt, minInt

            if minInt == maxInt:
                msg = 'The roll returns '
                msg += number.factorialBaseStr(minInt) + '!'
                if full:
                    msg += ' Value (base 10): ' + str(minInt)
                args.chat.send(msg)
                return True
            else:
                i = int(random.randint(minInt, maxInt))
                msg = f'The roll returns {number.factorialBaseStr(i)}!'
                if full:
                    msg += f''' \
Value (base 10): {i};  Min (base 10): {minInt}; Max (base 10): {maxInt}'''
                args.chat.send(msg)
                return True
        except Exception:
            pass
    else:
        baseI: Optional[int]
        try:
            baseI = int(base)
        except Exception:
            baseI = None
        if baseI is None:
            args.chat.send('The roll needs a valid base')
            return True
        if 0 <= baseI < 2:
            args.chat.send('The roll needs a base larger than or equal to 2')
            return True
        if baseI > 36:
            args.chat.send('The roll needs a base smaller than or equal to 36')
            return True
        if -1 <= baseI < 0:
            args.chat.send('The roll needs a base smaller than or equal to -2')
            return True
        if baseI < -36:
            args.chat.send('The roll needs a base larger than or equal to -36')
            return True
        try:
            if baseI < 0:
                minInt = baseI
                maxInt = baseI * baseI
                if len(args.message) == 1:
                    pass
                elif len(args.message) == 2:
                    minInt = 1
                    maxInt = number.negativeBaseInt(args.message[1], baseI)
                elif len(args.message) > 2:
                    minInt = number.negativeBaseInt(args.message[1], baseI)
                    maxInt = number.negativeBaseInt(args.message[2], baseI)

                if minInt > maxInt:
                    minInt, maxInt = maxInt, minInt

                if minInt == maxInt:
                    msg = f'''\
The roll returns {number.negativeBaseStr(minInt, baseI)}!'''
                    if full:
                        msg += f' Value (base 10): {minInt}'
                    args.chat.send(msg)
                    return True
                else:
                    i = int(random.randint(minInt, maxInt))
                    msg = f'''\
The roll returns {number.negativeBaseStr(i, baseI)}!'''
                    if full:
                        msg += f'''\
Value (base 10): {i}; Min (base 10): {minInt}; Max (base 10): {maxInt}'''
                    args.chat.send(msg)
                    return True
        except Exception:
            pass
        try:
            minInt = 1
            maxInt = int(baseI)
            if len(args.message) == 1:
                pass
            elif len(args.message) == 2:
                maxInt = int(args.message[1], baseI)
            elif len(args.message) > 2:
                minInt = int(args.message[1], baseI)
                maxInt = int(args.message[2], baseI)

            if minInt > maxInt:
                args.chat.send('The roll returns Kappa !')
                return True
            elif minInt == maxInt:
                msg = f'''\
The roll returns {number.positiveBaseStr(minInt, baseI)}!'''
                args.chat.send(msg)
                return True
            else:
                i = int(random.randint(minInt, maxInt))
                msg = f'The roll returns {number.positiveBaseStr(i, baseI)}!'
                args.chat.send(msg)
                return True
        except Exception:
            pass
    args.chat.send('The roll returns Kappa !')
    return True


@not_feature('noroll')
@permission('moderator')
async def commandChoice(args: ChatCommandArgs) -> bool:
    items = parser.parseArguments(args.message[1:])
    if len(args.message) <= 1:
        args.chat.send('Next time give me something to pick from')
        return True
    args.chat.send(f'I choose {random.choice(items)}!')
    return True
