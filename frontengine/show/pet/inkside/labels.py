"""Localized labels for built-in INKSIDE assets; third-party labels are shown as written."""
from __future__ import annotations

import re

from frontengine.utils.multi_language.retranslate import translate

PREFIX = 'inkside-'


def label(asset_identifier: str, text: str) -> str:
    """Translate a built-in part or garment label through the language dictionaries."""
    if not asset_identifier.startswith(PREFIX):
        return text
    return translate('inkside_' + re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_'), text)


def asset_label(asset) -> str:
    """'OUTFIT · Piece' keeps the outfit's proper name and localizes the piece."""
    if not asset.identifier.startswith(PREFIX) or ' · ' not in asset.name:
        return asset.name
    outfit, piece = asset.name.split(' · ', 1)
    return outfit + ' · ' + label(asset.identifier, piece)
