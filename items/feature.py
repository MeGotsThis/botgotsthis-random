from typing import Mapping, Optional


def features() -> Mapping[str, Optional[str]]:
    if not hasattr(features, 'features'):
        setattr(features, 'features', {
            'roll.exe': '!roll exe',
            'roll.emote': '!roll emotes',
            'noroll': 'Disable !roll',
            'winnerbroadcaster': '!winner only for broadcaster',
            })
    return getattr(features, 'features')
