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


def _edition(item: dict) -> tuple:
    return item.get("timestamp"), item.get("path")


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
        self.validated = {}          # id -> (timestamp, path) last staged without fault: no need to hash it again
        self._running = {}           # id -> edition the accepted job is processing
        self._latest = {}            # id -> newest installed item observed, for rescheduling after a job
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
            self._latest = {key: value for key, value in self._latest.items() if key in subscribed}
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
            self._latest[key] = dict(item)
            known = self.items.get(key)
            if known is not None and known.get("status") == "ready" and self.validated.get(key) == _edition(item):
                return
            self.items.setdefault(key, {**item, "status": "validating", "title": key})
            self.queue.append(dict(item))

    def _fill_queue(self) -> None:
        while self.queue and len(self.jobs.pending) < 2:
            item = self.queue.popleft()
            key, edition = item["id"], _edition(item)
            if key in self.jobs.pending:
                continue  # One job per item; _reschedule picks up the newest edition when it finishes.
            self._running[key] = edition
            self.jobs.submit(key, lambda value=item, done=edition: (done, self.cache.stage(value)))

    def _reschedule(self, key: str, processed) -> None:
        """Queue the newest observed edition again when the finished job handled an older one."""
        latest = self._latest.get(key)
        if latest is not None and _edition(latest) != processed:
            self.items[key].update(status="validating")
            self.queue.append(dict(latest))

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

    def _ready(self, key: str, result: tuple) -> None:
        self._running.pop(key, None)
        if key in self.items:
            processed, item = result
            self.items[key] = item
            self.validated[key] = processed
            self._reschedule(key, processed)
            self.changed.emit(list(self.items.values()))
        self._fill_queue()

    def _failed(self, key: str, error: str) -> None:
        processed = self._running.pop(key, None)
        if key in self.items:
            self.items[key].update(status="invalid", error=error)
            self._reschedule(key, processed)
            self.changed.emit(list(self.items.values()))
        self._fill_queue()

    def stop(self) -> None:
        self.timer.stop()
        self.queue.clear()
        self.jobs.stop()
