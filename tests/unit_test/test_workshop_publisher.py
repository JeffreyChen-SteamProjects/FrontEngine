"""Exercise publication side-effect ordering, recovery and native result boundaries."""
import ctypes as c
import json

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage

from frontengine.utils.steam.steam_runtime import APP_ID, CreateResult, DetailsResult, SteamEvent, SubmitResult
from frontengine.utils.workshop.workshop_publications import PublicationStore
from frontengine.utils.workshop.workshop_publisher import WorkshopPublisher


class Backend:
    initialized, user_id = True, 123

    def __init__(self):
        self.calls = []
        self.fail = ""
        self.raise_on = ""

    def call(self, name, *args):
        self.calls.append((name, args))
        if name == self.raise_on:
            raise OSError("Connection interrupted")
        if name == self.fail:
            return 0
        return {"CreateItem": 10, "RequestUGCDetails": 11, "StartItemUpdate": 20,
                "SubmitItemUpdate": 12}.get(name, True)


class Service(QObject):
    event_received = Signal(object)
    availability_changed = Signal(bool, str)
    stopping = Signal()

    def __init__(self):
        super().__init__()
        self.backend = Backend()


@pytest.fixture
def publication(tmp_path):
    source = tmp_path / "pet"
    source.mkdir()
    preview = tmp_path / "preview.png"
    image = QImage(16, 16, QImage.Format.Format_RGB32)
    image.fill(0xffffcc00)
    assert image.save(str(preview))
    assert image.save(str(source / "walk.png"))
    store = PublicationStore(123, tmp_path / "managed")
    record = store.prepare("pet_pack", source, "Pet", preview, "Description", ["Pet"])
    service = Service()
    publisher = WorkshopPublisher(service, store, clock=lambda: 10.0)
    yield publisher, service, store, record
    publisher.stop()


def send(service, callback, handle, result, failed=False):
    service.event_received.emit(SteamEvent(callback, bytes(result), handle, failed))


def created(publication, needs_terms=False):
    publisher, service, store, record = publication
    publisher.start(record["operation"])
    send(service, 3403, 10, CreateResult(1, 456, needs_terms))


def owned(service, owner=123, app=APP_ID):
    result = DetailsResult()
    result.details.item_id, result.details.result = 456, 1
    result.details.owner, result.details.consumer_app = owner, app
    send(service, 3402, 11, result)


def test_private_upload_persists_id_and_completes(publication):
    publisher, service, store, record = publication
    created(publication)
    saved = store.load(record["operation"])
    assert saved["published_id"] == "456"
    assert saved["state"] == "uploading"
    visibility = next(args for name, args in service.backend.calls if name == "SetItemVisibility")
    assert visibility == (20, 2)
    send(service, 3404, 12, SubmitResult(1, False, 456))
    assert store.load(record["operation"])["state"] == "completed"
    assert not publisher.timer.isActive()


def test_retry_failed_upload_checks_owner_and_never_recreates(publication):
    publisher, service, store, record = publication
    created(publication)
    send(service, 3404, 12, SubmitResult(15, False, 456))
    assert publisher.record["state"] == "failed"
    publisher.start(record["operation"])
    assert publisher.record["state"] == "verifying"
    owned(service)
    assert publisher.record["state"] == "uploading"
    assert sum(name == "CreateItem" for name, _ in service.backend.calls) == 1


@pytest.mark.parametrize("owner,app", [(999, APP_ID), (123, 480)])
def test_foreign_item_never_reaches_update(publication, owner, app):
    publisher, service, store, record = publication
    record["published_id"] = "456"
    store.save(record)
    publisher.start(record["operation"])
    owned(service, owner, app)
    assert publisher.record["state"] == "failed"
    assert not any(name == "StartItemUpdate" for name, _ in service.backend.calls)


def test_failed_setter_retains_id_without_submitting(publication):
    publisher, service, store, record = publication
    service.backend.fail = "SetItemPreview"
    created(publication)
    assert publisher.record["state"] == "failed"
    assert store.load(record["operation"])["published_id"] == "456"
    assert not any(name == "SubmitItemUpdate" for name, _ in service.backend.calls)


def test_terms_require_user_action_and_retry_same_id(publication):
    publisher, service, store, record = publication
    created(publication, needs_terms=True)
    assert publisher.record["state"] == "awaiting_terms"
    assert not any(name == "StartItemUpdate" for name, _ in service.backend.calls)
    publisher.start(record["operation"])
    owned(service)
    send(service, 3404, 12, SubmitResult(1, True, 456))
    assert publisher.record["state"] == "awaiting_terms"


@pytest.mark.parametrize("payload,failed", [(b"short", False), (bytes(CreateResult(1, 456, False)), True)])
def test_invalid_result_is_uncertain_and_never_blindly_recreated(publication, payload, failed):
    publisher, service, store, record = publication
    publisher.start(record["operation"])
    service.event_received.emit(SteamEvent(3403, payload, 10, failed))
    assert publisher.record["state"] == "outcome_unknown"
    with pytest.raises(ValueError, match="Creation outcome"):
        publisher.start(record["operation"])
    assert len(service.backend.calls) == 1


def test_shutdown_during_upload_retains_snapshot_and_unknown_outcome(publication):
    publisher, service, store, record = publication
    created(publication)
    service.stopping.emit()
    assert publisher.record["state"] == "outcome_unknown"
    assert not publisher.timer.isActive()
    assert (store.directory(record["operation"]) / "snapshot").is_dir()
    publisher.start(record["operation"])
    assert publisher.record["state"] == "verifying"


def test_connection_failure_during_submit_is_not_reported_as_cancelled(publication):
    publisher, service, store, record = publication
    service.backend.raise_on = "SubmitItemUpdate"
    created(publication)
    assert publisher.record["state"] == "outcome_unknown"
    assert store.load(record["operation"])["published_id"] == "456"


def test_timeout_and_unrelated_callback(publication):
    publisher, service, store, record = publication
    publisher.start(record["operation"])
    send(service, 3403, 99, CreateResult(1, 456, False))
    assert publisher.record["state"] == "creating"
    publisher.clock = lambda: 9999
    publisher._tick()
    assert publisher.record["state"] == "outcome_unknown"


def test_recovery_is_explicit_and_does_not_disturb_live_operation(publication):
    publisher, service, store, record = publication
    publisher.start(record["operation"])
    assert store.records()[0]["state"] == "creating"
    assert store.records(recover=True)[0]["state"] == "outcome_unknown"


def test_changed_snapshot_rejected_before_any_network_call(publication):
    publisher, service, store, record = publication
    snapshot = store.directory(record["operation"]) / "snapshot"
    manifest = json.loads((snapshot / "workshop.json").read_text(encoding="utf-8"))
    manifest["title"] = "Different title"
    (snapshot / "workshop.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="snapshot has changed"):
        publisher.start(record["operation"])
    assert service.backend.calls == []


def test_storage_account_and_paths_cannot_be_swapped(publication):
    publisher, service, store, record = publication
    with pytest.raises(ValueError):
        store.directory("../" + "a" * 29)
    record["user_id"] = "999"
    store.save(record)
    with pytest.raises(ValueError, match="account"):
        publisher.start(record["operation"])
    assert service.backend.calls == []


def test_invalid_metadata_rejected_before_publication(publication):
    publisher, service, store, record = publication
    record["visibility"] = "public"
    store.save(record)
    with pytest.raises(ValueError, match="visibility"):
        publisher.start(record["operation"])
    assert service.backend.calls == []


def test_progress_uses_native_byte_counters(publication):
    publisher, service, store, record = publication
    received = []
    publisher.progress.connect(lambda *values: received.append(values))
    created(publication)
    original = service.backend.call
    def call(name, *args):
        if name == "GetItemUpdateProgress":
            c.cast(args[1], c.POINTER(c.c_uint64)).contents.value = 10
            c.cast(args[2], c.POINTER(c.c_uint64)).contents.value = 20
            return 3
        return original(name, *args)
    service.backend.call = call
    publisher._tick()
    assert received == [(3, 10, 20)]
