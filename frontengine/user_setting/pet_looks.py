"""Where a pet's own look comes from, so the pet home can draw picture and Puppet pets as themselves.

A pet profile records a layered character (the wardrobe) but not the picture a desktop pet
was started with. The pet page records it here when it starts a pet:

* ``sprite`` - the GIF/PNG/WebP/JPEG file or the sprite-pack folder the desktop pet uses;
* ``portrait`` - a still of a Puppet pet, rendered by its own canvas (never a screenshot) and
  saved as ``pet-home-looks/<id>.png``, because a Puppet rig cannot run inside the home.

The registry lives in the settings under ``pet_home_looks`` and is checked at the boundary:
unknown ids, kinds and paths are ignored, a sprite must still be a regular picture file or
folder, and a portrait is only ever read from its own file in the looks folder.
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
SPRITE_EXTENSIONS = (".gif", ".webp", ".png", ".jpg", ".jpeg")
MAX_SPRITE_BYTES = 64 * 1024 * 1024
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


def checked_sprite(path: str | Path) -> Path | None:
    """A sprite file or sprite-pack folder that may be read, or None."""
    candidate = Path(path)
    if not candidate.is_absolute() or candidate.is_symlink():
        return None
    if candidate.is_dir():
        return candidate
    if (candidate.is_file() and candidate.suffix.lower() in SPRITE_EXTENSIONS
            and 0 < candidate.stat().st_size <= MAX_SPRITE_BYTES):
        return candidate
    return None


def remember_sprite(settings: dict, identifier: str, path: str | Path) -> bool:
    """Record the picture a desktop pet was started with; False when it is not one that may be read."""
    if not isinstance(identifier, str) or not _ID.fullmatch(identifier) or len(str(path)) > MAX_PATH:
        return False
    checked = checked_sprite(Path(path).resolve())
    if checked is None:
        return False
    _registry(settings)[identifier] = {"kind": "sprite", "path": str(checked)}
    return True


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
    path = entry.get("path")
    if entry.get("kind") == "sprite" and set(entry) == {"kind", "path"} and isinstance(path, str) \
            and len(path) <= MAX_PATH:
        checked = checked_sprite(path)
        return ("sprite", checked) if checked is not None else None
    return None
