"""Real content round trips and untrusted Workshop boundary regressions."""
import json
import zipfile

import pytest
from PySide6.QtGui import QImage

from frontengine.user_setting.preset_repository import PresetRepository
from frontengine.utils.scene_format.scene_package import save_package
from frontengine.utils.workshop.workshop_content import classify_item, preset_files
from frontengine.utils.workshop.workshop_manifest import FORMAT, read_manifest, safe_path
from frontengine.utils.workshop.workshop_package import create_snapshot, validate_content


@pytest.fixture
def preview(tmp_path):
    path = tmp_path / "preview.png"
    image = QImage(16, 16, QImage.Format.Format_RGB32)
    image.fill(0xffffd740)
    assert image.save(str(path))
    return path


@pytest.mark.parametrize("kind", ["scene", "preset", "pet_pack"])
def test_snapshot_payload_round_trip(tmp_path, preview, kind):
    if kind == "scene":
        source = tmp_path / "source.fescene"
        save_package({"image": {"type": "IMAGE", "file_path": str(preview)}}, source)
    elif kind == "preset":
        repository = PresetRepository(tmp_path / "presets")
        repository.save("Test", {"image": {"file_path": str(preview)}})
        source = repository.export_package("Test", tmp_path / "preset.zip")
    else:
        source = tmp_path / "pet"
        source.mkdir()
        (source / "walk.png").write_bytes(preview.read_bytes())
        (source / "pet.json").write_text('{"name": "Pet"}', encoding="utf-8")
    output = tmp_path / "snapshot"
    manifest = create_snapshot(kind, source, "My content", preview, output)
    assert validate_content(output) == manifest
    assert classify_item(output) == kind
    assert preset_files(output) == [], "Manifest must not be imported as a preset"
    assert not list(tmp_path.glob(".workshop-*"))


@pytest.mark.parametrize("entry", ["../outside", "/outside", "C:/outside", "..\\outside"])
def test_resource_escape_is_rejected(tmp_path, entry):
    with pytest.raises(ValueError):
        safe_path(tmp_path, entry)


def test_unknown_json_and_malformed_manifest_do_not_become_presets(tmp_path):
    (tmp_path / "data.json").write_text('{"unexpected": true}', encoding="utf-8")
    assert classify_item(tmp_path) is None
    (tmp_path / "workshop.json").write_text('{"format": "wrong"}', encoding="utf-8")
    (tmp_path / "settings.json").write_text('{"image": {}}', encoding="utf-8")
    assert classify_item(tmp_path) is None


def test_unknown_version_is_rejected(tmp_path):
    (tmp_path / "content").mkdir()
    (tmp_path / "workshop.json").write_text(json.dumps({
        "format": FORMAT, "version": 2, "kind": "pet_pack", "title": "Pack", "entry": "content"}),
        encoding="utf-8")
    with pytest.raises(ValueError, match="version"):
        read_manifest(tmp_path)


def test_failed_snapshot_never_creates_destination(tmp_path, preview):
    source = tmp_path / "broken.fescene"
    source.write_bytes(b"not a scene")
    target = tmp_path / "snapshot"
    with pytest.raises((ValueError, zipfile.BadZipFile)):
        create_snapshot("scene", source, "Broken", preview, target)
    assert not target.exists()
    assert not list(tmp_path.glob(".workshop-*"))


def test_executable_pet_pack_is_rejected(tmp_path, preview):
    source = tmp_path / "pet"
    source.mkdir()
    (source / "walk.png").write_bytes(preview.read_bytes())
    (source / "plugin.py").write_text('raise RuntimeError("must never run")', encoding="utf-8")
    with pytest.raises(ValueError, match="Executable"):
        create_snapshot("pet_pack", source, "Pet", preview, tmp_path / "snapshot")


def test_preset_flat_filename_collision_is_rejected_before_extraction(tmp_path):
    source = tmp_path / "bad.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("preset.json", "{}")
        archive.writestr("media/a/image.png", "first")
        archive.writestr("media/b/image.png", "second")
    repository = PresetRepository(tmp_path / "presets")
    with pytest.raises(ValueError, match="colliding"):
        repository.import_package(source)
    assert not repository.directory.exists()
