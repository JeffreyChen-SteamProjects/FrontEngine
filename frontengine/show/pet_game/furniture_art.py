"""Furniture pictures rendered in Blender (tools/blender_furniture.py), one set per theme.

Images ship as package data under ``furniture/<theme>/<definition>.png``. One
grid cell is 96 pixels wide in the file and the bottom edge is the floor, so a
picture scales to its footprint width and keeps its own height. Pieces with no
picture (content that brings none) are drawn as labelled blocks instead.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QImage

FOLDER = Path(__file__).resolve().parent / "furniture"
ITEM_FOLDER = Path(__file__).resolve().parent / "items"
# Where a pet using the piece rests, as a fraction of the picture's height above the floor:
# a sleeping pet lies on the mattress, a relaxing one sits on the cushion.
SURFACES = {"bed_basic": 0.42, "bed_cozy": 0.44, "armchair": 0.3, "cat_tree": 0.8, "climbing_wall": 0.86}
_CACHE: dict[tuple[str, str], QImage | None] = {}
# Content packs' pictures, already checked by content_pack: furniture id -> theme -> file.
PACK_PICTURES: dict[str, dict[str, Path]] = {}


def register_pack_pictures(pictures: dict[str, dict[str, Path]]) -> None:
    PACK_PICTURES.update(pictures)
    _CACHE.clear()


def _candidates(theme: str, definition: str) -> list[Path]:
    pack = PACK_PICTURES.get(definition)
    if pack is not None:
        return [path for path in (pack.get(theme), pack.get("warm_home")) if path is not None]
    return [FOLDER / folder / f"{definition}.png" for folder in (theme, "warm_home")]


def picture(theme: str, definition: str) -> QImage | None:
    """The piece's picture in this theme, falling back to the warm home set; None if there is none."""
    key = (theme, definition)
    if key not in _CACHE:
        image = None
        for path in _candidates(theme, definition):
            if path.is_file():
                candidate = QImage(str(path))
                if not candidate.isNull():
                    image = candidate
                    break
        _CACHE[key] = image
    return _CACHE[key]


def aspect(theme: str, definition: str) -> float | None:
    """Height divided by width, or None without a picture."""
    image = picture(theme, definition)
    return image.height() / image.width() if image is not None else None


_ITEMS: dict[str, QImage | None] = {}


def item_picture(identifier: str) -> QImage | None:
    """An item's Blender icon (``items/<id>.png``: wood, herb, flower, toy, coin, letter, story), or None."""
    if identifier not in _ITEMS:
        path = ITEM_FOLDER / f"{identifier}.png"
        image = QImage(str(path)) if path.is_file() and path.parent == ITEM_FOLDER else None
        _ITEMS[identifier] = image if image is not None and not image.isNull() else None
    return _ITEMS[identifier]
