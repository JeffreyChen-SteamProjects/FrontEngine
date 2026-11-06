"""Qt manager integration without real network, Steam publication or media playback."""
import time
import pytest
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import QCoreApplication
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
        dialog.jobs.pool.waitForDone(100)
        QCoreApplication.processEvents()
    assert not dialog.jobs.pending


@pytest.mark.parametrize('operation', ['source_file', 'source_folder', 'preview', 'preset'])
@pytest.mark.parametrize('destroy', [False, True])
def test_closed_workshop_discards_modal_choice(tmp_path, monkeypatch, lifetime_factory, operation, destroy):
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QFileDialog, QInputDialog
    from shiboken6 import isValid
    from frontengine.utils.workshop.workshop_cache import WorkshopCache

    owner = QWidget()
    owner.lifetime = lifetime_factory()
    backend = Backend()
    service = WorkshopService(owner, backend)
    dialog = WorkshopDialog(owner, service, tmp_path / 'storage')
    dialog.cache = WorkshopCache(123, tmp_path / 'cache')
    dialog.kind.setCurrentIndex(dialog.kind.findData('pet_pack' if operation == 'source_folder' else 'scene'))
    dialog.show()
    before = (dialog.source.text(), dialog.preview.text(), dialog.title.text())
    requested = []
    monkeypatch.setattr(dialog.jobs, 'submit', lambda key, function: requested.append(key))
    def retire():
        dialog.reject()
        if destroy:
            dialog.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    def choose_file(*_args):
        retire()
        return str(tmp_path / 'chosen.png'), ''
    def choose_folder(*_args):
        retire()
        return str(tmp_path)
    def choose_name(*_args, **_kwargs):
        retire()
        return 'Imported', True
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', choose_file)
    monkeypatch.setattr(QFileDialog, 'getExistingDirectory', choose_folder)
    monkeypatch.setattr(QInputDialog, 'getText', choose_name)
    try:
        if operation == 'preset':
            dialog._load_item(dict(kind='preset', path=str(tmp_path), id='456', title='Preset'))
        elif operation == 'preview':
            dialog._choose_preview()
        else:
            dialog._choose_source()
        assert requested == []
        assert not backend.initialized
        if isValid(dialog):
            assert (dialog.source.text(), dialog.preview.text(), dialog.title.text()) == before
        def unexpected(*_args, **_kwargs):
            pytest.fail('Closed Workshop reopened a modal')
        monkeypatch.setattr(QFileDialog, 'getOpenFileName', unexpected)
        monkeypatch.setattr(QFileDialog, 'getExistingDirectory', unexpected)
        monkeypatch.setattr(QInputDialog, 'getText', unexpected)
        dialog._choose_source()
        dialog._choose_preview()
        dialog._load_item(dict(kind='preset', path=str(tmp_path), id='456', title='Preset'))
    finally:
        service.stop()
        if isValid(dialog):
            dialog.close()
        owner.close()


def test_workshop_preset_close_cancel_reopen_then_import(tmp_path, monkeypatch, lifetime_factory):
    from PySide6.QtWidgets import QInputDialog
    from frontengine.user_setting.preset_repository import PresetRepository
    from frontengine.utils.workshop.workshop_cache import WorkshopCache
    from frontengine.utils.workshop.workshop_package import create_snapshot

    monkeypatch.chdir(tmp_path)
    owner = QWidget()
    owner.lifetime = lifetime_factory()
    backend = Backend()
    service = WorkshopService(owner, backend)
    dialog = WorkshopDialog(owner, service, tmp_path / 'storage')
    source = PresetRepository(tmp_path / 'source-presets')
    source.save('Original', {'text': {'text': 'Keep these values'}})
    package = source.export_package('Original', tmp_path / 'preset.zip')
    preview = tmp_path / 'preview.png'
    image = QImage(16, 16, QImage.Format.Format_RGB32)
    image.fill(0xff123456)
    assert image.save(str(preview))
    snapshot = tmp_path / 'download'
    create_snapshot('preset', package, 'Preset', preview, snapshot)
    dialog.cache = WorkshopCache(123, tmp_path / 'cache')
    ready = dialog.cache.stage({'id': '456', 'path': str(snapshot), 'state': 5})
    target = PresetRepository(tmp_path / 'presets')
    choices = iter([('ClosedImport', True), ('CancelledImport', False), ('Imported', True)])
    def answer(*_args, **_kwargs):
        name, accepted = next(choices)
        if name == 'ClosedImport':
            dialog.reject()
        return name, accepted
    monkeypatch.setattr(QInputDialog, 'getText', answer)
    try:
        dialog.show()
        dialog._load_item(ready)
        flush_jobs(dialog)
        assert not target.exists('ClosedImport')
        dialog.show()
        dialog._load_item(ready)
        assert not dialog.jobs.pending and not target.exists('CancelledImport')
        dialog._load_item(ready)
        flush_jobs(dialog)
        assert target.load('Imported') == source.load('Original')
        assert not backend.initialized
        assert dialog.cache.stage({'id': '456', 'path': str(snapshot), 'state': 5})['status'] == 'ready'
    finally:
        service.stop()
        dialog.close()
        owner.close()


@pytest.mark.parametrize('operation', ['source_file', 'source_folder', 'preview'])
def test_workshop_picker_cancel_reopen_then_retry(tmp_path, monkeypatch, lifetime_factory, operation):
    from PySide6.QtWidgets import QFileDialog

    owner = QWidget()
    owner.lifetime = lifetime_factory()
    backend = Backend()
    service = WorkshopService(owner, backend)
    dialog = WorkshopDialog(owner, service, tmp_path / 'storage')
    dialog.kind.setCurrentIndex(dialog.kind.findData('pet_pack' if operation == 'source_folder' else 'scene'))
    chosen = tmp_path / ('assets' if operation == 'source_folder' else 'chosen.png')
    if operation == 'source_folder':
        chosen.mkdir()
    else:
        image = QImage(16, 16, QImage.Format.Format_RGB32)
        image.fill(0xffccdd00)
        assert image.save(str(chosen))
    answers = iter(['', str(chosen)])
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *_args: (next(answers), ''))
    monkeypatch.setattr(QFileDialog, 'getExistingDirectory', lambda *_args: next(answers))
    choose = dialog._choose_preview if operation == 'preview' else dialog._choose_source
    try:
        dialog.show()
        choose()
        assert (dialog.source.text(), dialog.preview.text(), dialog.title.text()) == ('', '', '')
        dialog.reject()
        dialog.show()
        choose()
        if operation == 'preview':
            assert dialog.preview.text() == str(chosen)
            assert dialog.source.text() == dialog.title.text() == ''
        else:
            assert dialog.source.text() == str(chosen)
            assert dialog.title.text() == chosen.stem
            assert dialog.preview.text() == ''
        assert not backend.initialized
        assert not dialog.jobs.pending
    finally:
        service.stop()
        dialog.close()
        owner.close()


def test_workshop_description_tab_moves_focus_without_changing_text(tmp_path, lifetime_factory):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    owner = QWidget()
    owner.lifetime = lifetime_factory()
    service = WorkshopService(owner, Backend())
    dialog = WorkshopDialog(owner, service, tmp_path / 'storage')
    try:
        dialog.show()
        dialog.activateWindow()
        dialog.description.setPlainText('Description')
        dialog.description.setFocus()
        QCoreApplication.processEvents()
        QTest.keyClick(dialog.description, Qt.Key.Key_Tab)
        assert dialog.tags.hasFocus()
        assert dialog.description.toPlainText() == 'Description'
        QTest.keyClick(dialog.tags, Qt.Key.Key_Backtab)
        assert dialog.description.hasFocus()
        QTest.keyClick(dialog.description, Qt.Key.Key_End)
        QTest.keyClick(dialog.description, Qt.Key.Key_Return)
        QTest.keyClicks(dialog.description, 'Second line')
        assert dialog.description.toPlainText() == 'Description\nSecond line'
    finally:
        service.stop()
        dialog.close()
        owner.close()


def test_dialog_is_lazy_and_close_does_not_cancel_upload(tmp_path, lifetime_factory):
    owner = QWidget()
    owner.lifetime = lifetime_factory()
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


def test_shutdown_marks_upload_uncertain_before_runtime_release(tmp_path, lifetime_factory):
    owner = QWidget()
    owner.lifetime = lifetime_factory()
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


def test_scene_load_adopts_package_lease_on_gui_thread(tmp_path, lifetime_factory):
    from frontengine.user_setting.scene_setting import scene_json, release_scene_packages
    from frontengine.utils.scene_format.scene_package import save_package
    from frontengine.utils.workshop.workshop_package import create_snapshot
    owner = QWidget()
    owner.lifetime = lifetime_factory()
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
