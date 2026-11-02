"""Create immutable, bounded publication snapshots from supported local content."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

from frontengine.user_setting.preset_repository import PresetRepository
from frontengine.utils.imervue.puppet_asset import checked_members, read_json_member
from frontengine.utils.scene_format.scene_package import load_package, save_package
from frontengine.utils.workshop.workshop_manifest import (
    FORMAT, VERSION, checked_tree, read_manifest, safe_path,
)

PET_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}


def validate_content(root: Path) -> dict:
    """Validate all files and the actual packaged payload before it is used."""
    checked_tree(root)
    manifest = read_manifest(root)
    entry = safe_path(root, manifest["entry"])
    if manifest["kind"] == "scene":
        entries, lease = load_package(entry)
        lease.cleanup()
        if not entries:
            raise ValueError("A Workshop scene must contain at least one layer")
    elif manifest["kind"] == "preset":
        with zipfile.ZipFile(entry) as archive:
            checked_members(archive)
            read_json_member(archive, "preset.json")
        with tempfile.TemporaryDirectory(prefix="frontengine-preset-check-") as directory:
            PresetRepository(Path(directory)).import_package(entry)
    elif manifest["kind"] in ("home_furniture", "home_theme"):
        _validate_home_pack(manifest["kind"], entry)
    elif manifest["kind"] == "home_blueprint":
        _validate_blueprint(entry)
    else:
        _validate_pet(entry)
    return manifest


def _validate_home_pack(kind: str, source: Path):
    """The pet home's own checks; a furniture item must bring pieces, a theme item themes."""
    from frontengine.utils.pet_game.content_pack import load_pack
    pack = load_pack(source)
    if kind == "home_furniture" and not pack.furniture:
        raise ValueError("A Workshop furniture pack must contain furniture")
    if kind == "home_theme" and not pack.themes:
        raise ValueError("A Workshop theme must contain a theme")
    return pack


def _validate_blueprint(source: Path) -> str:
    """Parse a blueprint and return it rewritten from its checked parts only."""
    from frontengine.utils.pet_game.blueprint import MAX_BLUEPRINT_BYTES, canonical_blueprint
    if source.is_symlink() or not source.is_file() or source.stat().st_size > MAX_BLUEPRINT_BYTES:
        raise ValueError("A blueprint must be a regular file of at most 128 KiB")
    return canonical_blueprint(source.read_text(encoding="utf-8"))


def requirements(kind: str, source: Path) -> list[str]:
    """The content packs a home item needs besides itself, written into its manifest."""
    if kind == "home_blueprint":
        from frontengine.utils.pet_game.blueprint import required_packs
        return required_packs(_validate_blueprint(source))
    return []


def _validate_pet(source: Path) -> None:
    pictures = [p for p in checked_tree(source) if p.suffix.lower() in PET_EXTENSIONS]
    if not pictures:
        raise ValueError("A pet pack must contain sprite images")
    from PySide6.QtGui import QImageReader
    for image in pictures:
        reader = QImageReader(str(image))
        size = reader.size()
        if not reader.canRead() or not 0 < size.width() * size.height() <= 16_777_216:
            raise ValueError(f"Invalid or oversized sprite: {image.name}")
    manifest = source / "pet.json"
    if manifest.exists():
        if manifest.stat().st_size > 64 * 1024:
            raise ValueError("Pet manifest exceeds its size limit")
        if not isinstance(json.loads(manifest.read_text(encoding="utf-8")), dict):
            raise ValueError("Pet manifest must be an object")


def _copy_home_pack(kind: str, source: Path, content: Path) -> str:
    """Copy only the manifest, the thumbnail and furniture pictures; the folder keeps the pack id."""
    pack = _validate_home_pack(kind, source)
    target = content / pack.identifier
    target.mkdir()
    for path in checked_tree(source):
        relative = path.relative_to(source)
        if relative.as_posix() in ("pack.json", "thumbnail.png") or (
                relative.parts[0] == "furniture" and path.suffix.lower() == ".png"):
            output = target / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, output)
    return f"content/{pack.identifier}"


def _copy_payload(kind: str, source: Path, content: Path) -> str:
    if source.is_symlink() or getattr(source.lstat(), "st_file_attributes", 0) & 0x400:
        raise ValueError("Publication sources cannot be links or junctions")
    if kind in ("home_furniture", "home_theme"):
        return _copy_home_pack(kind, source, content)
    if kind == "home_blueprint":                  # only the checked layout: nothing personal can ride along
        (content / "blueprint.json").write_text(_validate_blueprint(source), encoding="utf-8")
        return "content/blueprint.json"
    if kind == "pet_pack":
        _validate_pet(source)
        target = content / "pet-pack"
        target.mkdir()
        for path in checked_tree(source):
            if path.suffix.lower() not in PET_EXTENSIONS and path.name != "pet.json":
                continue
            relative = path.relative_to(source)
            output = target / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, output)
        return "content/pet-pack"
    if not source.is_file() or source.stat().st_size > 256 * 1024 * 1024:
        raise ValueError("Publication source exceeds its size limit")
    if kind == "scene":
        target = content / "scene.fescene"
        if source.suffix.lower() == ".fescene":
            shutil.copyfile(source, target)
        else:
            from frontengine.utils.scene_format.scene_3d_document import read_scene_document
            entries = read_scene_document(json.loads(source.read_text(encoding="utf-8")), source.parent)
            save_package(entries, target)
        return "content/scene.fescene"
    if kind == "preset":
        shutil.copyfile(source, content / "preset.zip")
        return "content/preset.zip"
    raise ValueError("Unsupported Workshop content kind")


def create_snapshot(kind: str, source: Path, title: str, preview: Path,
                    destination: Path) -> dict:
    """Publish only explicit resources into a new directory; never overwrite a snapshot."""
    from PySide6.QtGui import QImageReader
    if (preview.is_symlink() or not preview.is_file() or preview.stat().st_size >= 1_000_000 or
            getattr(preview.lstat(), "st_file_attributes", 0) & 0x400):
        raise ValueError("Preview must be a regular image smaller than 1 MB")
    if not QImageReader(str(preview)).canRead():
        raise ValueError("Preview is not a readable image")
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".workshop-", dir=destination.parent) as directory:
        root = Path(directory)
        (root / "content").mkdir()
        entry = _copy_payload(kind, source, root / "content")
        suffix = preview.suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg"}:
            raise ValueError("Preview format must be PNG or JPEG")
        shutil.copyfile(preview, root / ("preview" + suffix))
        manifest = {"format": FORMAT, "version": VERSION, "kind": kind,
                    "title": title, "entry": entry, "content_revision": 1,
                    "min_frontengine_version": "1.0.81", "required_capabilities": [],
                    "requires": requirements(kind, source)}
        (root / "workshop.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        manifest = validate_content(root)
        # Move the validated tree as a unit, never exposing a partially copied item.
        os.rename(root, destination)
    return manifest
