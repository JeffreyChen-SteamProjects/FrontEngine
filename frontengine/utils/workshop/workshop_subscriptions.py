"""Download callbacks, install-state checks and asynchronous subscription validation."""
from __future__ import annotations

import ctypes as c
from collections import deque

from PySide6.QtCore import QObject, QTimer, Signal

from frontengine.utils.steam.steam_runtime import APP_ID, PACK, U32, U64, I32
from frontengine.utils.workshop.workshop_jobs import WorkshopJobs


class DownloadResult(c.Structure):
    _pack_ = PACK
    _fields_ = [("app_id", U32), ("item_id", U64), ("result", I32)]


class InstalledResult(c.Structure):
    _pack_ = PACK
    _fields_ = [("app_id", U32), ("item_id", U64), ("legacy_content", U64), ("manifest_id", U64)]


class WorkshopSubscriptions(QObject):
    changed = Signal(object)
    failed = Signal(str)

    def __init__(self, service, cache, parent=None, jobs=None) -> None:
        super().__init__(parent)
        self.service, self.cache = service, cache
        self.jobs = jobs or WorkshopJobs(self)
        self.items = {}
        self.downloads = set()
        self.queue = deque()
        self.jobs.completed.connect(self._ready)
        self.jobs.failed.connect(self._failed)
        service.event_received.connect(self._event)
        service.stopping.connect(self.stop)
        self.timer = QTimer(self)
        self.timer.setInterval(20000)
        self.timer.timeout.connect(self.refresh)

    def refresh(self) -> None:
        if not self.service.backend.initialized:
            return
        try:
            installed = self.service.backend.subscribed_items()
            subscribed = {item["id"] for item in installed}
            self.items = {key: value for key, value in self.items.items() if key in subscribed}
            self.downloads.intersection_update(subscribed)
            self.queue.clear()
            for item in installed:
                self._update(item)
            self._fill_queue()
            self.changed.emit(list(self.items.values()))
            self.timer.start()
        except (OSError, RuntimeError, ValueError) as error:
            self.failed.emit(str(error))

    def _update(self, item: dict) -> None:
        key = item["id"]
        state = item["state"]
        if not state & 4 or state & (8 | 16 | 32):
            self.items[key] = {**item, "status": "downloading", "title": key}
            if key not in self.downloads:
                if self.service.backend.call("DownloadItem", int(key), False):
                    self.downloads.add(key)
                else:
                    self.items[key].update(status="failed", error="Steam rejected the download")
        elif item["path"]:
            self.items.setdefault(key, {**item, "status": "validating", "title": key})
            self.queue.append(dict(item))

    def _fill_queue(self) -> None:
        while self.queue and len(self.jobs.pending) < 2:
            item = self.queue.popleft()
            self.jobs.submit(item["id"], lambda value=item: self.cache.stage(value))

    def _event(self, event) -> None:
        structure = {3405: InstalledResult, 3406: DownloadResult}.get(event.callback)
        if structure is None or event.failed or len(event.payload) != c.sizeof(structure):
            return
        result = structure.from_buffer_copy(event.payload)
        key = str(result.item_id)
        if result.app_id != APP_ID or key not in self.items:
            return
        if event.callback == 3406:
            if key not in self.downloads:
                return
            self.downloads.discard(key)
            if result.result != 1:
                self.items[key].update(status="failed", error=f"Steam download failed (EResult {result.result})")
                self.changed.emit(list(self.items.values()))
                return
        # Re-query flags/locations rather than trusting an event-provided filesystem path.
        self.refresh()

    def _ready(self, key: str, item: dict) -> None:
        if key in self.items:
            self.items[key] = item
            self.changed.emit(list(self.items.values()))
        self._fill_queue()

    def _failed(self, key: str, error: str) -> None:
        if key in self.items:
            self.items[key].update(status="invalid", error=error)
            self.changed.emit(list(self.items.values()))
        self._fill_queue()

    def stop(self) -> None:
        self.timer.stop()
        self.queue.clear()
        self.jobs.stop()
