"""Bounded color choices shared by asset and profile validation."""
import re

_TOKEN = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}')
_COLOR = re.compile(r'#[0-9a-fA-F]{6}')


def checked_palette(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or len(value) > 8:
        raise ValueError('A palette supports at most eight color regions')
    for key, color in value.items():
        if (not isinstance(key, str) or not _TOKEN.fullmatch(key)
                or not isinstance(color, str) or not _COLOR.fullmatch(color)):
            raise ValueError('Palette regions require identifiers and #RRGGBB colors')
    return dict(value)


def checked_colors(value: object) -> dict[str, dict[str, str]]:
    if not isinstance(value, dict) or len(value) > 5:
        raise ValueError('An outfit supports color overrides for at most five assets')
    result = {}
    for key, colors in value.items():
        if (not isinstance(key, str) or len(key.split('@')) != 2
                or any(not _TOKEN.fullmatch(part) for part in key.split('@'))):
            raise ValueError('Color overrides require an exact asset ID@version')
        result[key] = checked_palette(colors)
    return result
