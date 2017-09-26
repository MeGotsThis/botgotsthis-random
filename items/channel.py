from typing import Iterable, Mapping, Optional

from lib.data import ChatCommand

from .. import channel


def filterMessage() -> Iterable[ChatCommand]:
    yield channel.logLastMessage


def commands() -> Mapping[str, Optional[ChatCommand]]:
    if not hasattr(commands, 'commands'):
        setattr(commands, 'commands', {
            '!winner': channel.commandWinner,
            '!setnolurk': channel.commandSetNoLurk,
            '!roll': channel.commandRoll,
            '!choose': channel.commandChoice,
            }
        )
    return getattr(commands, 'commands')


def commandsStartWith() -> Mapping[str, Optional[ChatCommand]]:
    if not hasattr(commandsStartWith, 'commands'):
        setattr(commandsStartWith, 'commands', {
            '!roll-': channel.commandRollBase,
            }
        )
    return getattr(commandsStartWith, 'commands')


def processNoCommand() -> Iterable[ChatCommand]:
    return []
