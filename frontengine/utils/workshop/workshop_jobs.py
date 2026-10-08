"""Bounded Qt worker jobs for Workshop validation, hashing and file copying."""
from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal


class JobSignals(QObject):
    finished = Signal(str, object, str)


class Job(QRunnable):
    def __init__(self, key: str, function, signals: JobSignals) -> None:
        super().__init__()
        self.key, self.function, self.signals = key, function, signals

    def run(self) -> None:
        try:
            result, error = self.function(), ""
        except Exception as exception:  # Workers report errors instead of aborting the application.
            result, error = None, str(exception)
        self.signals.finished.emit(self.key, result, error)


class WorkshopJobs(QObject):
    completed = Signal(str, object)
    failed = Signal(str, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.pool = QThreadPool.globalInstance()
        self.pending = {}
        self.closed = False

    def submit(self, key: str, function) -> bool:
        if self.closed or key in self.pending or len(self.pending) >= 2:
            return False
        signals = JobSignals()
        signals.finished.connect(self._finished, Qt.ConnectionType.QueuedConnection)
        self.pending[key] = signals
        self.pool.start(Job(key, function, signals))
        return True

    def _finished(self, key: str, result, error: str) -> None:
        self.pending.pop(key, None)
        if not self.closed:
            if error:
                self.failed.emit(key, error)
            else:
                self.completed.emit(key, result)

    def stop(self) -> None:
        # Active bounded copies may finish; no callback can mutate a closing UI.
        self.closed = True
