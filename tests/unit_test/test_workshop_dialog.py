"""Qt manager integration without real network, Steam publication or media playback."""
import time
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import QCoreApplication, QThreadPool
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QWidget

from frontengine.ui.dialog.workshop_dialog import WorkshopDialog
from frontengine.utils.steam.steam_runtime import CreateResult, SteamEvent, SubmitResult
from frontengine.utils.workshop.workshop_service import WorkshopService


class Backend:
    reason, initialized, user_id = "", False, 123

    def initialize(self):
        self.initialized = True
        return True

    def shutdown(self):
        self.initialized = False

    def poll(self):
        return []

    def subscribed_items(self):
        return []

    def call(self, name, *args):
        return {"CreateItem": 10, "StartItemUpdate": 20, "SubmitItemUpdate": 12}.get(name, True)


def flush_jobs(dialog):
    deadline = time.monotonic() + 5
    while dialog.jobs.pending and time.monotonic() < deadline:
        QThreadPool.globalInstance().waitForDone(100)
        QCoreApplication.processEvents()
    assert not dialog.jobs.pending


def test_dialog_is_lazy_and_close_does_not_cancel_upload(tmp_path):
    owner = QWidget()
    backend = Backend()
    service = WorkshopService(owner, backend)
    dialog = WorkshopDialog(owner, service, tmp_path / "storage")
    dialog._error = lambda reason: (_ for _ in ()).throw(AssertionError(reason))
    assert not backend.initialized
    dialog.connect_steam()
    assert backend.initialized
    source = tmp_path / "pet"
    source.mkdir()
    preview = tmp_path / "preview.png"
    image = QImage(16, 16, QImage.Format.Format_RGB32)
    image.fill(0xffccdd00)
    assert image.save(str(preview))
    assert image.save(str(source / "walk.png"))
    dialog.select_source("pet_pack", str(source))
    dialog.preview.setText(str(preview))
    assert dialog.visibility.currentData() == 2
    dialog._prepare()
    flush_jobs(dialog)
    assert dialog.publisher.record["state"] == "creating"
    service.event_received.emit(SteamEvent(3403, bytes(CreateResult(1, 456, False)), 10))
    dialog.close()
    assert dialog.publisher.busy
    assert dialog.publisher.record["state"] == "uploading"
    service.event_received.emit(SteamEvent(3404, bytes(SubmitResult(1, False, 456)), 12))
    assert dialog.publisher.record["state"] == "completed"
    assert dialog.published_id.text() == "456"
    service.stop()
    assert dialog.jobs.closed and not backend.initialized
    owner.close()


def test_shutdown_marks_upload_uncertain_before_runtime_release(tmp_path):
    owner = QWidget()
    backend = Backend()
    service = WorkshopService(owner, backend)
    dialog = WorkshopDialog(owner, service, tmp_path)
    dialog.connect_steam()
    dialog.publisher.record = {"version": 1, "operation": "a" * 32, "state": "uploading",
                               "app_id": 2793470, "user_id": "123", "published_id": "456",
                               "manifest": {"title": "Test"}, "error": ""}
    dialog.store.directory("a" * 32).mkdir()
    service.stop()
    assert dialog.publisher.record["state"] == "outcome_unknown"
    assert not dialog.publisher.timer.isActive()
    assert dialog.jobs.closed
    owner.close()


def test_scene_load_adopts_package_lease_on_gui_thread(tmp_path):
    from frontengine.user_setting.scene_setting import scene_json, release_scene_packages
    from frontengine.utils.scene_format.scene_package import save_package
    from frontengine.utils.workshop.workshop_package import create_snapshot
    owner = QWidget()
    refreshed = []
    owner.scene_setting_ui = SimpleNamespace(scene_manager_ui=SimpleNamespace(renew_json_plain_text=lambda: refreshed.append(True)))
    service = WorkshopService(owner, Backend())
    dialog = WorkshopDialog(owner, service, tmp_path / "storage")
    dialog.connect_steam()
    image = QImage(16, 16, QImage.Format.Format_RGB32)
    image.fill(0xffffcc00)
    preview = tmp_path / "preview.png"
    image.save(str(preview))
    source = tmp_path / "source.fescene"
    save_package({"test": {"type": "IMAGE", "file_path": str(preview)}}, source)
    snapshot = tmp_path / "download"
    create_snapshot("scene", source, "Scene", preview, snapshot)
    ready = dialog.cache.stage({"id": "456", "path": str(snapshot), "state": 5})
    dialog._load_item(ready)
    flush_jobs(dialog)
    assert refreshed
    asset = Path(scene_json["test"]["file_path"])
    assert asset.is_file()
    service.stop()
    release_scene_packages()
    assert not asset.exists()
    owner.close()


def test_preset_import_preserves_existing_name_and_does_not_mutate_cache(tmp_path):
    import pytest
    from frontengine.user_setting.preset_repository import PresetRepository
    from frontengine.utils.workshop.workshop_cache import WorkshopCache
    from frontengine.utils.workshop.workshop_package import create_snapshot
    repository = PresetRepository(tmp_path / "presets")
    repository.save("Original", {"text": {"text": "Hello"}})
    package = repository.export_package("Original", tmp_path / "preset.zip")
    image = QImage(16, 16, QImage.Format.Format_RGB32)
    image.fill(0xffffcc00)
    preview = tmp_path / "preview.png"
    image.save(str(preview))
    snapshot = tmp_path / "download"
    create_snapshot("preset", package, "Preset", preview, snapshot)
    cache = WorkshopCache(123, tmp_path / "cache")
    ready = cache.stage({"id": "456", "path": str(snapshot), "state": 5})
    with pytest.raises(ValueError, match="already exists"):
        cache.import_preset(ready, "Original", repository)
    assert cache.import_preset(ready, "Imported", repository) == "Imported"
    assert repository.load("Imported") == repository.load("Original")
    assert cache.stage({"id": "456", "path": str(snapshot), "state": 5})["status"] == "ready"


def test_runtime_build_validation_rejects_wrong_architecture(tmp_path):
    import importlib.util
    import pytest
    specification = importlib.util.spec_from_file_location("build_exe", Path(__file__).parents[2] / "exe/build_exe.py")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    path = tmp_path / "steam_api64.dll"
    path.write_bytes(b"not a DLL")
    with pytest.raises(ValueError, match="Windows DLL"):
        module.validated_runtime(str(path))
    data = bytearray(70)
    data[:2], data[60:64], data[64:70] = b"MZ", (64).to_bytes(4, "little"), b"PE\0\0\x4c\x01"
    path.write_bytes(data)
    with pytest.raises(ValueError, match="x64"):
        module.validated_runtime(str(path))
    data[68:70] = b"\x64\x86"
    path.write_bytes(data)
    assert module.validated_runtime(str(path)) == path


def test_workshop_demo_scene_creates_playable_layer():
    import json
    from frontengine.show.scene.scene import SceneManager
    source = Path(__file__).parents[2] / "docs/formats/workshop-demo.scene.json"
    scene = SceneManager()
    try:
        entries = json.loads(source.read_text(encoding="utf-8"))["entries"]
        for entry in entries.values():
            scene.add_text(entry)
        assert len(scene.widget_list) == 1
        assert not scene.widget_list[0].widget().output_frame().isNull()
    finally:
        scene.clear()
