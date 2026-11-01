"""Furniture content packs: a folder with a manifest and pictures, checked before anything is used.

A pack lives in its own folder under ``pet-home-packs``::

    pet-home-packs/<pack id>/pack.json
    pet-home-packs/<pack id>/thumbnail.png
    pet-home-packs/<pack id>/furniture/<theme>/<art>.png

``pack.json`` names the pack (format, version, stable id, name, source, licence) and lists
its furniture (id, name, category, footprint, interaction points, what it is used for, the
poses it wants, price and comfort). Everything is checked at this boundary: unknown fields,
paths that leave the pack (``..``, links), oversized pictures, duplicate ids and any file that
could run (scripts or programs) reject the whole pack, and the reason is reported. Nothing in
a pack is executed. Furniture ids become ``<pack>__<id>`` so packs never collide with the
built-in pieces or with each other; a save that still holds a removed pack's pieces keeps
them dormant until the pack comes back.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from frontengine.utils.pet_game.catalog import (
    ACTIVITIES, CATEGORIES, NEEDS, POSES, PROFESSIONS, Catalog, FurnitureDefinition, builtin_catalog,
    check_furniture,
)
from frontengine.utils.pet_game.layout import THEMES

PACK_FOLDER = "pet-home-packs"
PACK_FORMAT = "frontengine.home-pack"
PACK_VERSION = 1
MANIFEST = "pack.json"
MAX_MANIFEST_BYTES = 64 * 1024
MAX_PACKS = 32
MAX_PACK_FURNITURE = 64
MAX_PICTURE_BYTES = 2 * 1024 * 1024
MAX_PACK_FILES = 400
# Anything that could run is refused outright, whatever it claims to be.
FORBIDDEN_SUFFIXES = {".py", ".pyc", ".pyw", ".js", ".mjs", ".exe", ".dll", ".so", ".dylib", ".bat", ".cmd",
                      ".ps1", ".sh", ".vbs", ".jar", ".msi", ".com", ".scr", ".lnk", ".html", ".htm"}
_PACK_ID = re.compile(r"[a-z][a-z0-9_]{0,23}")
_LOCAL_ID = re.compile(r"[a-z][a-z0-9_]{0,21}")
_PACK_FIELDS = {"format", "version", "id", "name", "source", "license", "furniture"}
_PIECE_FIELDS = {"id", "name", "category", "width", "solid", "points", "activity", "effects", "price", "comfort",
                 "poses", "profession", "art"}
_OPTIONAL_PIECE_FIELDS = {"points", "activity", "effects", "price", "comfort", "poses", "profession", "art"}


@dataclass
class ContentPack:
    identifier: str
    name: str
    source: str
    license: str
    root: Path
    furniture: list[FurnitureDefinition] = field(default_factory=list)
    pictures: dict[str, dict[str, Path]] = field(default_factory=dict)    # furniture id -> theme -> png


def _text(value: object, limit: int, label: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= limit or any(ord(c) < 32 for c in value):
        raise ValueError(f"Invalid pack {label}")
    return value.strip()


def _int(value: object, low: int, high: int, label: str) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"Invalid pack {label}")
    return value


def _inside(root: Path, candidate: Path) -> bool:
    """True only for a regular file below the pack folder, reached without any link."""
    try:
        resolved = candidate.resolve(strict=True)
    except OSError:
        return False
    current = candidate
    while current != root:
        if current.is_symlink():
            return False
        current = current.parent
    return resolved.is_relative_to(root.resolve()) and resolved.is_file()


def _check_files(root: Path) -> None:
    """Refuse a pack holding anything that could run, too many files, or a link leading out."""
    count = 0
    for path in root.rglob("*"):
        count += 1
        if count > MAX_PACK_FILES:
            raise ValueError("Pack has too many files")
        if path.is_symlink():
            raise ValueError("Pack contains a link")
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            raise ValueError(f"Pack contains a file that could run: {path.name}")


def _picture(root: Path, theme: str, art: str) -> Path | None:
    candidate = root / "furniture" / theme / f"{art}.png"
    if not candidate.exists():
        return None
    if not _inside(root, candidate) or candidate.stat().st_size > MAX_PICTURE_BYTES:
        raise ValueError(f"Invalid pack picture {theme}/{art}.png")
    with candidate.open("rb") as stream:
        if stream.read(8) != b"\x89PNG\r\n\x1a\n":
            raise ValueError(f"Pack picture is not a PNG: {theme}/{art}.png")
    return candidate


def _piece(raw: object, pack: str) -> tuple[FurnitureDefinition, str]:
    if not isinstance(raw, dict) or not set(raw) <= _PIECE_FIELDS or not (_PIECE_FIELDS - _OPTIONAL_PIECE_FIELDS) <= set(raw):
        raise ValueError("Invalid pack furniture fields")
    local = raw["id"]
    if not isinstance(local, str) or not _LOCAL_ID.fullmatch(local):
        raise ValueError("Invalid pack furniture id")
    if raw["category"] not in CATEGORIES or raw.get("activity") not in (None, *ACTIVITIES):
        raise ValueError("Unknown pack furniture category or use")
    if raw.get("profession") not in (None, *PROFESSIONS) or not isinstance(raw["solid"], bool):
        raise ValueError("Invalid pack furniture")
    effects = raw.get("effects", {})
    if not isinstance(effects, dict) or set(effects) - set(NEEDS):
        raise ValueError("Invalid pack furniture effects")
    poses = raw.get("poses", [])
    if not isinstance(poses, list) or any(pose not in POSES for pose in poses):
        raise ValueError("Invalid pack furniture poses")
    points = raw.get("points", [])
    if not isinstance(points, list):
        raise ValueError("Invalid pack furniture points")
    art = raw.get("art", local)
    if not isinstance(art, str) or not _LOCAL_ID.fullmatch(art):
        raise ValueError("Invalid pack furniture art")
    price = _int(raw.get("price", 0), 0, 10000, "price")
    identifier = f"{pack}__{local}"
    definition = FurnitureDefinition(
        identifier, "pack_" + identifier, _text(raw["name"], 64, "furniture name"), raw["category"],
        _int(raw["width"], 1, 8, "width"), raw["solid"], tuple(_int(p, 0, 7, "point") for p in points),
        raw.get("activity"), {need: _int(rate, -60, 60, "effect") for need, rate in effects.items()},
        price=price, sell_back=price // 2, comfort=_int(raw.get("comfort", 0), 0, 5, "comfort"),
        profession=raw.get("profession"), use_ms=(30000, 60000) if raw.get("activity") in ("play", "relax") else (0, 0),
        poses=tuple(poses))
    check_furniture(definition)
    return definition, art


def load_pack(root: Path) -> ContentPack:
    """Read and check one pack folder; raises ValueError with the reason when it is refused."""
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Not a pack folder")
    _check_files(root)
    manifest = root / MANIFEST
    if not _inside(root, manifest) or manifest.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("Missing or oversized pack.json")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if (not isinstance(data, dict) or set(data) != _PACK_FIELDS or data["format"] != PACK_FORMAT
            or data["version"] != PACK_VERSION):
        raise ValueError("Not a FrontEngine home pack (format, version or fields)")
    identifier = data["id"]
    if not isinstance(identifier, str) or not _PACK_ID.fullmatch(identifier) or identifier != root.name:
        raise ValueError("The pack id must match its folder name")
    raw_furniture = data["furniture"]
    if not isinstance(raw_furniture, list) or not 1 <= len(raw_furniture) <= MAX_PACK_FURNITURE:
        raise ValueError("A pack holds 1 to 64 pieces of furniture")
    pack = ContentPack(identifier, _text(data["name"], 64, "name"), _text(data["source"], 200, "source"),
                       _text(data["license"], 64, "license"), root)
    for raw in raw_furniture:
        definition, art = _piece(raw, identifier)
        if any(other.identifier == definition.identifier for other in pack.furniture):
            raise ValueError(f"Duplicate furniture id in pack: {definition.identifier}")
        pictures = {theme: path for theme in THEMES if (path := _picture(root, theme, art)) is not None}
        if "warm_home" not in pictures:
            raise ValueError(f"Pack furniture needs a warm_home picture: {art}.png")
        pack.furniture.append(definition)
        pack.pictures[definition.identifier] = pictures
    return pack


def load_packs(folder: Path) -> tuple[list[ContentPack], dict[str, str]]:
    """Every acceptable pack in the folder, and the reason each refused folder was refused."""
    packs, errors, seen = [], {}, set()
    if not folder.is_dir():
        return packs, errors
    for root in sorted(path for path in folder.iterdir() if path.is_dir() or path.is_symlink())[:MAX_PACKS]:
        try:
            pack = load_pack(root)
            if pack.identifier in seen:
                raise ValueError("Duplicate pack id")
        except (OSError, ValueError, UnicodeDecodeError) as error:
            errors[root.name] = str(error)
            continue
        seen.add(pack.identifier)
        packs.append(pack)
    return packs, errors


def catalog_with_packs(packs: list[ContentPack]) -> Catalog:
    """The built-in catalog plus the packs' furniture, through the catalog's own checks."""
    base = builtin_catalog()
    furniture = list(base.furniture.values()) + [piece for pack in packs for piece in pack.furniture]
    return Catalog(furniture, list(base.recipes.values()), list(base.items.values()))
