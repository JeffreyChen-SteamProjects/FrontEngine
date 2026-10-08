"""Validate versioned Workshop content before importing or publishing it."""
from __future__ import annotations

import json
import re
import stat
from pathlib import Path, PurePosixPath

FORMAT = "frontengine.workshop"
VERSION = 1
KINDS = ("scene", "preset", "pet_pack")
MAX_BYTES = 256 * 1024 * 1024
MAX_FILES = 4096
MAX_MANIFEST_BYTES = 64 * 1024
FORBIDDEN_SUFFIXES = {".py", ".pyc", ".pyd", ".dll", ".exe", ".so", ".bat", ".cmd", ".ps1"}
PRESET_KEYS = {"video", "image", "web", "gif", "sound", "text", "particle", "pet",
               "wallpaper", "widgets", "focus", "screen_care", "presentation", "tools"}


def safe_path(root: Path, relative: str) -> Path:
    """Resolve a portable relative path without traversing links or junctions."""
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise ValueError("Invalid Workshop resource path")
    path = PurePosixPath(relative)
    if path.is_absolute() or any(part in ("..", ".") for part in path.parts) or "\0" in relative:
        raise ValueError("Unsafe Workshop resource path")
    base = root.resolve()
    target = base
    for part in path.parts:
        target /= part
        if target.is_symlink() or (target.exists() and
                getattr(target.lstat(), "st_file_attributes", 0) & 0x400):
            raise ValueError("Workshop resources cannot be links or junctions")
    if not target.resolve().is_relative_to(base):
        raise ValueError("Workshop resource is outside its item")
    return target


def checked_tree(root: Path) -> list[Path]:
    """Return bounded regular resources; reject executable content and links."""
    if root.is_symlink() or not root.is_dir() or getattr(root.lstat(), "st_file_attributes", 0) & 0x400:
        raise ValueError("Workshop item must be a regular directory")
    pending, files, total = [root], [], 0
    count = 0
    while pending:
        for path in pending.pop().iterdir():
            count += 1
            if count > MAX_FILES:
                raise ValueError("Workshop item exceeds its file limit")
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise ValueError("Workshop resources cannot be links or junctions")
            if path.is_dir():
                pending.append(path)
            elif stat.S_ISREG(info.st_mode):
                if path.suffix.lower() in FORBIDDEN_SUFFIXES:
                    raise ValueError("Executable Workshop content is not supported")
                total += info.st_size
                if total > MAX_BYTES:
                    raise ValueError("Workshop item exceeds its byte limit")
                files.append(path)
            else:
                raise ValueError("Workshop resource is not a regular file")
    return files


def validate_manifest(value: object, root: Path) -> dict:
    """Validate an envelope and its confined, existing content entry."""
    if not isinstance(value, dict) or value.get("format") != FORMAT:
        raise ValueError("Not a FrontEngine Workshop manifest")
    if type(value.get("version")) is not int or value["version"] != VERSION:
        raise ValueError("Unsupported Workshop manifest version")
    if value.get("kind") not in KINDS:
        raise ValueError("Unsupported Workshop content kind")
    title = value.get("title")
    if not isinstance(title, str) or not title.strip() or "\0" in title or len(title.encode("utf-8")) > 128:
        raise ValueError("Workshop title must contain 1–128 UTF-8 bytes")
    entry = safe_path(root, value.get("entry"))
    if not (entry.is_dir() if value["kind"] == "pet_pack" else entry.is_file()):
        raise ValueError("Workshop entry is missing or has the wrong type")
    revision = value.get("content_revision", 1)
    if type(revision) is not int or revision < 1:
        raise ValueError("Invalid Workshop content revision")
    minimum = value.get("min_frontengine_version", "1.0.81")
    if not isinstance(minimum, str) or not re.fullmatch(r"\d+\.\d+\.\d+", minimum):
        raise ValueError("Invalid minimum FrontEngine version")
    capabilities = value.get("required_capabilities", [])
    if not isinstance(capabilities, list) or any(not isinstance(v, str) for v in capabilities):
        raise ValueError("Invalid required capabilities")
    return {**value, "title": title.strip(), "content_revision": revision,
            "min_frontengine_version": minimum, "required_capabilities": capabilities}


def read_manifest(root: Path) -> dict:
    """Read a bounded UTF-8 manifest; malformed new items never use legacy fallback."""
    path = safe_path(root, "workshop.json")
    if path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("Workshop manifest exceeds its size limit")
    return validate_manifest(json.loads(path.read_text(encoding="utf-8")), root)


def is_legacy_preset(path: Path) -> bool:
    """Recognize known preset settings while retaining legacy empty presets."""
    if path.name.lower() in {"workshop.json", "plugin.json", "pet.json"}:
        return False
    try:
        if path.stat().st_size > MAX_MANIFEST_BYTES:
            return False
        data = json.loads(path.read_text(encoding="utf-8"))
        return isinstance(data, dict) and "format" not in data and (
            not data or "__preset_name__" in data or bool(PRESET_KEYS.intersection(data)))
    except (OSError, ValueError, UnicodeError):
        return False
