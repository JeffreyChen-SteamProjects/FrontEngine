"""Where a Puppet pet's own look comes from, so the pet home can draw it as itself.

A pet profile records a layered character (the wardrobe), which the home draws directly. A
Puppet pet has none, so the pet page records a ``portrait`` here: a still rendered by the
Puppet's own canvas (never a screenshot) and saved as ``pet-home-looks/<id>.png``, because a
Puppet rig cannot run inside the home.

The registry lives in the settings under ``pet_home_looks`` and is checked at the boundary:
unknown ids and kinds are ignored (``sprite`` entries from before pets were layered only among
them), and a portrait is only ever read from its own file in the looks folder.
"""
from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

LOOKS_KEY = "pet_home_looks"
LOOK_FOLDER = "pet-home-looks"
MAX_PATH = 1024
PORTRAIT_HEIGHT = 256
_ID = re.compile(r"[0-9a-f]{32}")


def looks_folder() -> Path:
    return Path.cwd() / LOOK_FOLDER


def _registry(settings: dict) -> dict:
    looks = settings.get(LOOKS_KEY)
    if not isinstance(looks, dict):
        looks = {}
        settings[LOOKS_KEY] = looks
    return looks


def remember_portrait(settings: dict, identifier: str, image: QImage, folder: Path | None = None) -> bool:
    """Save a still of a Puppet pet (atomically, at most PORTRAIT_HEIGHT tall) and record it."""
    if not isinstance(identifier, str) or not _ID.fullmatch(identifier) or image.isNull():
        return False
    folder = folder or looks_folder()
    folder.mkdir(parents=True, exist_ok=True)
    if image.height() > PORTRAIT_HEIGHT:
        image = image.scaledToHeight(PORTRAIT_HEIGHT, Qt.TransformationMode.SmoothTransformation)
    handle, temporary = tempfile.mkstemp(suffix=".png", dir=folder)
    os.close(handle)
    try:
        if not image.save(temporary, "PNG"):
            return False
        os.replace(temporary, folder / f"{identifier}.png")
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)
    _registry(settings)[identifier] = {"kind": "portrait"}
    return True


def look_for(settings: dict, identifier: str, folder: Path | None = None) -> tuple[str, Path] | None:
    """``(kind, path)`` for this pet's own look, or None when there is none that can be used now."""
    looks = settings.get(LOOKS_KEY)
    if not isinstance(looks, dict) or not isinstance(identifier, str) or not _ID.fullmatch(identifier):
        return None
    entry = looks.get(identifier)
    if not isinstance(entry, dict):
        return None
    if entry.get("kind") == "portrait" and set(entry) == {"kind"}:
        portrait = (folder or looks_folder()) / f"{identifier}.png"
        return ("portrait", portrait) if portrait.is_file() and not portrait.is_symlink() else None
    return None
