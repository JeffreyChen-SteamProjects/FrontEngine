"""Subscription versions, conflict handling and event validation."""
import ctypes as c
import json
import time

import pytest
from PySide6.QtCore import QObject, Signal, QCoreApplication, QThreadPool
from PySide6.QtGui import QImage

from frontengine.utils.steam.steam_runtime import APP_ID, SteamEvent
from frontengine.utils.workshop.workshop_cache import WorkshopCache
from frontengine.utils.workshop.workshop_jobs import WorkshopJobs
from frontengine.utils.workshop.workshop_subscriptions import DownloadResult, InstalledResult, WorkshopSubscriptions


@pytest.fixture
def installed(tmp_path):
    source = tmp_path / "steam" / "456"
    source.mkdir(parents=True)
    image = QImage(16, 16, QImage.Format.Format_RGB32)
    image.fill(0xff00ccff)
    assert image.save(str(source / "walk.png"))
    (source / "pet.json").write_text('{"name":"Pet"}', encoding="utf-8")
    return {"id": "456", "path": str(source), "state": 5, "timestamp": 10}, WorkshopCache(123, tmp_path / "cache")


def test_cache_copies_validated_content_without_mutating_steam(installed):
    item, cache = installed
    ready = cache.stage(item)
    assert ready["status"] == "ready"
    assert ready["title"] == "Pet"
    assert ready["path"] != item["path"]
    assert cache.current("456")["path"] == ready["path"]
    assert (cache.entry(ready) / "walk.png").read_bytes() == (cache.entry(item) / "walk.png").read_bytes()
    assert not list(cache.directory("456").glob(".download-*"))


def test_updates_preserve_old_open_scene_version(installed):
    item, cache = installed
    first = cache.stage(item)
    (cache.entry(item) / "pet.json").write_text('{"name":"Updated"}', encoding="utf-8")
    second = cache.stage(item)
    assert first["path"] != second["path"]
    assert cache.entry(first).is_dir()
    assert cache.current("456")["title"] == "Updated"


def test_local_changes_create_conflict_until_explicit_activation(installed):
    item, cache = installed
    first = cache.stage(item)
    (cache.entry(first) / "pet.json").write_text('{"name":"Local edit"}', encoding="utf-8")
    (cache.entry(item) / "pet.json").write_text('{"name":"New download"}', encoding="utf-8")
    candidate = cache.stage(item)
    assert candidate["status"] == "conflict"
    assert cache.current("456")["title"] == "Local edit"
    cache.activate(candidate)
    assert cache.current("456")["title"] == "New download"
    assert cache.entry(first).is_dir()


@pytest.mark.parametrize("state", [1, 13, 21, 37])
def test_pending_download_never_reads_install_files(installed, state):
    item, cache = installed
    item.update(state=state, path="this-path-does-not-exist")
    with pytest.raises(ValueError, match="downloading"):
        cache.stage(item)
    assert not cache.directory("456").exists()


def test_invalid_version_does_not_replace_current(installed):
    item, cache = installed
    first = cache.stage(item)
    (cache.entry(item) / "workshop.json").write_text('{"format":"invalid"}', encoding="utf-8")
    with pytest.raises(ValueError):
        cache.stage(item)
    assert cache.current("456")["path"] == first["path"]


def test_case_sensitive_legacy_preset_and_executable_rejection(tmp_path):
    from frontengine.utils.workshop.workshop_cache import validate_installed
    (tmp_path / "Settings.JSON").write_text('{"image":{}}', encoding="utf-8")
    assert validate_installed(tmp_path)["kind"] == "preset"
    (tmp_path / "plugin.py").write_text("print('unsafe')", encoding="utf-8")
    with pytest.raises(ValueError, match="Executable"):
        validate_installed(tmp_path)


class FakeJobs(QObject):
    completed = Signal(str, object)
    failed = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.pending = {}
        self.stopped = False

    def submit(self, key, function):
        self.pending[key] = function

    def stop(self):
        self.stopped = True


class Service(QObject):
    event_received = Signal(object)
    stopping = Signal()
    initialized = True

    def __init__(self, item):
        super().__init__()
        self.backend = self
        self.installed = [item]
        self.calls = []

    def subscribed_items(self):
        return self.installed

    def call(self, name, *args):
        self.calls.append((name, args))
        return True


def test_download_checks_app_id_request_and_actual_install_state(installed):
    item, cache = installed
    item["state"] = 1
    service, jobs = Service(item), FakeJobs()
    subscriptions = WorkshopSubscriptions(service, cache, jobs=jobs)
    subscriptions.refresh()
    assert service.calls == [("DownloadItem", (456, False))]
    assert not jobs.pending
    for callback in [DownloadResult(480, 456, 1), DownloadResult(APP_ID, 999, 1)]:
        service.event_received.emit(SteamEvent(3406, bytes(callback)))
    assert subscriptions.downloads == {"456"}
    item["state"] = 5
    service.event_received.emit(SteamEvent(3406, bytes(DownloadResult(APP_ID, 456, 1))))
    assert not subscriptions.downloads
    assert "456" in jobs.pending
    subscriptions.stop()
    assert not subscriptions.timer.isActive() and jobs.stopped


def test_failed_download_exposes_result_and_malformed_events_are_ignored(installed):
    item, cache = installed
    item["state"] = 1
    service, jobs = Service(item), FakeJobs()
    subscriptions = WorkshopSubscriptions(service, cache, jobs=jobs)
    subscriptions.refresh()
    service.event_received.emit(SteamEvent(3406, b"short"))
    assert "456" in subscriptions.downloads
    service.event_received.emit(SteamEvent(3406, bytes(DownloadResult(APP_ID, 456, 15))))
    assert subscriptions.items["456"]["status"] == "failed"
    assert "15" in subscriptions.items["456"]["error"]
    subscriptions.stop()


def test_unsubscribed_content_is_not_reintroduced_by_late_worker(installed):
    item, cache = installed
    service, jobs = Service(item), FakeJobs()
    subscriptions = WorkshopSubscriptions(service, cache, jobs=jobs)
    subscriptions.refresh()
    service.installed = []
    subscriptions.refresh()
    jobs.pending.pop("456")
    jobs.completed.emit("456", {"id": "456"})
    assert subscriptions.items == {}
    subscriptions.stop()


def test_worker_delivers_on_gui_thread_and_suppresses_shutdown_callbacks():
    import threading
    jobs = WorkshopJobs()
    main_thread = threading.get_ident()
    delivered = []
    jobs.completed.connect(lambda key, result: delivered.append((threading.get_ident(), result)))
    assert jobs.submit("first", lambda: threading.get_ident())
    QThreadPool.globalInstance().waitForDone(3000)
    deadline = time.monotonic() + 3
    while not delivered and time.monotonic() < deadline:
        QCoreApplication.processEvents()
    assert delivered[0][0] == main_thread
    assert delivered[0][1] != main_thread
    jobs.stop()
    assert not jobs.submit("second", lambda: 1)


def test_download_structures_match_windows_sdk():
    import sys
    if sys.platform == "win32":
        assert [c.sizeof(DownloadResult), DownloadResult.item_id.offset, DownloadResult.result.offset] == [24, 8, 16]
        assert [c.sizeof(InstalledResult), InstalledResult.item_id.offset, InstalledResult.manifest_id.offset] == [32, 8, 24]


def test_cache_index_cannot_escape_version_root(installed):
    item, cache = installed
    cache.stage(item)
    index = cache.directory("456") / "current.json"
    index.write_text(json.dumps({"version": "../outside", "hashes": {}}), encoding="utf-8")
    with pytest.raises(ValueError, match="Unsafe"):
        cache.current("456")
