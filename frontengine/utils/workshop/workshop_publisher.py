"""Steam publication state machine with durable IDs and explicit uncertain outcomes."""
from __future__ import annotations

import ctypes as c
import json
import time

from PySide6.QtCore import QObject, QTimer, Signal

from frontengine.utils.steam.steam_runtime import (
    APP_ID, CreateResult, DetailsResult, StringArray, SubmitResult, U64,
)
from frontengine.utils.workshop.workshop_publications import PENDING, PublicationStore, item_id


class WorkshopPublisher(QObject):
    """Own one upload; closing the UI cannot pretend to cancel Steam's submission."""
    changed = Signal(object)
    progress = Signal(int, int, int)

    def __init__(self, service, store: PublicationStore, parent=None, clock=None) -> None:
        super().__init__(parent)
        self.service, self.store = service, store
        self.clock = clock or time.monotonic
        self.record = None
        self.handle = self.update_handle = self.expected = 0
        self.deadline = 0.0
        self.timer = QTimer(self)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self._tick)
        service.event_received.connect(self._event)
        service.availability_changed.connect(self._availability)
        service.stopping.connect(self.stop)

    @property
    def busy(self) -> bool:
        return self.record is not None and self.record["state"] in PENDING

    def start(self, operation: str) -> None:
        if self.busy:
            raise RuntimeError("Another Workshop publication is still running")
        backend = self.service.backend
        if not backend.initialized or backend.user_id != self.store.user_id:
            raise RuntimeError("The publication belongs to another or unavailable Steam session")
        record = self.store.load(operation)
        if record["state"] in PENDING:
            raise ValueError("Recover interrupted operations before retrying")
        if record["state"] == "outcome_unknown" and not record["published_id"]:
            raise ValueError("Creation outcome is unknown; check your Steam Workshop before creating again")
        self.record = record
        self.update_handle = 0
        try:
            if record["published_id"]:
                self._wait("verifying", 3402, "RequestUGCDetails", item_id(record["published_id"]), 0)
            else:
                # Save intent before issuing CreateItem: a crash must not trigger blind recreation.
                self._wait("creating", 3403, "CreateItem", APP_ID, 0)
        except (OSError, RuntimeError, ValueError) as error:
            self._state("outcome_unknown", str(error))

    def _state(self, state: str, error: str = "") -> None:
        self.record.update(state=state, error=error)
        self.store.save(self.record)
        if state not in PENDING:
            self.timer.stop()
            self.handle = self.expected = 0
        self.changed.emit(dict(self.record))

    def _wait(self, state: str, callback: int, function: str, *arguments) -> None:
        self._state(state)
        self.expected = callback
        self.deadline = self.clock() + (1800 if state == "uploading" else 120)
        self.handle = self.service.backend.call(function, *arguments)
        if not self.handle or self.handle == (1 << 64) - 1:
            self._state("failed", f"Steam rejected {function}")
            return
        self.timer.start()

    def _event(self, event) -> None:
        if not self.busy or event.call_handle != self.handle:
            return
        if event.callback != self.expected or event.failed:
            self._state("outcome_unknown", "Steam did not return a valid operation result")
            return
        structure = {3402: DetailsResult, 3403: CreateResult, 3404: SubmitResult}[event.callback]
        if len(event.payload) != c.sizeof(structure):
            self._state("outcome_unknown", "Unexpected Steam result layout")
            return
        result = structure.from_buffer_copy(event.payload)
        try:
            self._result(event.callback, result)
        except (OSError, RuntimeError, ValueError) as error:
            self._state("outcome_unknown" if self.record["state"] == "uploading" else "failed", str(error))

    def _result(self, callback: int, result) -> None:
        if callback == 3402:
            detail = result.details
            if (detail.result != 1 or detail.owner != self.store.user_id or
                    detail.consumer_app != APP_ID or detail.item_id != item_id(self.record["published_id"])):
                raise ValueError("Steam item is unavailable or does not belong to this account/application")
            self._submit()
        elif callback == 3403:
            # Retain a returned ID even if Steam also reports an error or unaccepted terms.
            if result.item_id:
                self.record["published_id"] = str(item_id(result.item_id))
                self.store.save(self.record)
            if result.result != 1 or not result.item_id:
                raise ValueError(f"Steam CreateItem failed (EResult {result.result})")
            if result.needs_terms:
                self._state("awaiting_terms", "Accept the Steam Workshop agreement before retrying")
            else:
                self._submit()
        else:
            if result.item_id != item_id(self.record["published_id"]):
                self._state("outcome_unknown", "Steam returned a different published ID")
            elif result.result != 1:
                self._state("failed", f"Steam upload failed (EResult {result.result})")
            else:
                self._state("awaiting_terms" if result.needs_terms else "completed",
                            "Accept the Steam Workshop agreement" if result.needs_terms else "")

    def _submit(self) -> None:
        backend, record = self.service.backend, self.record
        self.update_handle = backend.call("StartItemUpdate", APP_ID, item_id(record["published_id"]))
        if not self.update_handle or self.update_handle == (1 << 64) - 1:
            raise ValueError("Steam rejected StartItemUpdate")
        snapshot = self.store.directory(record["operation"]) / "snapshot"
        preview = next(snapshot.glob("preview.*"))
        metadata = json.dumps({"format": "frontengine.workshop", "version": 1,
                               "operation": record["operation"], "kind": record["manifest"]["kind"]})
        values = {"Title": record["manifest"]["title"], "Description": record["description"],
                  "Metadata": metadata, "Content": str(snapshot), "Preview": str(preview)}
        for suffix, value in values.items():
            if not backend.call("SetItem" + suffix, self.update_handle, value.encode("utf-8")):
                raise ValueError("Steam rejected SetItem" + suffix)
        strings = (c.c_char_p * len(record["tags"]))(*(t.encode("utf-8") for t in record["tags"]))
        tags = StringArray(strings, len(strings))
        if not backend.call("SetItemTags", self.update_handle, c.byref(tags), False):
            raise ValueError("Steam rejected item tags")
        if not backend.call("SetItemVisibility", self.update_handle, record["visibility"]):
            raise ValueError("Steam rejected item visibility")
        self._wait("uploading", 3404, "SubmitItemUpdate", self.update_handle, b"FrontEngine content update")

    def _tick(self) -> None:
        if not self.busy:
            return
        if self.clock() > self.deadline:
            self._state("outcome_unknown", "Steam operation timed out; verify the item before retrying")
            return
        if self.record["state"] == "uploading":
            try:
                processed, total = U64(), U64()
                phase = self.service.backend.call("GetItemUpdateProgress", self.update_handle,
                                                   c.byref(processed), c.byref(total))
                self.progress.emit(phase, processed.value, total.value)
            except (OSError, RuntimeError, ValueError) as error:
                self._state("outcome_unknown", str(error))

    def _availability(self, available: bool, reason: str) -> None:
        if not available and self.busy:
            self.stop(reason)

    def stop(self, reason: str = "Steam session stopped before the result arrived") -> None:
        self.timer.stop()
        if self.busy:
            self._state("outcome_unknown", reason)
