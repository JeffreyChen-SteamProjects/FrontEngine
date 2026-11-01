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
# Where a pet using the piece rests, as a fraction of the picture's height above the floor:
# a sleeping pet lies on the mattress, a relaxing one sits on the cushion.
SURFACES = {"bed_basic": 0.42, "bed_cozy": 0.44, "armchair": 0.3}
_CACHE: dict[tuple[str, str], QImage | None] = {}


def picture(theme: str, definition: str) -> QImage | None:
    """The piece's picture in this theme, falling back to the warm home set; None if there is none."""
    key = (theme, definition)
    if key not in _CACHE:
        image = None
        for folder in (theme, "warm_home"):
            path = FOLDER / folder / f"{definition}.png"
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
