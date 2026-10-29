"""Lazy local document jobs with one detached result and no GUI-thread file I/O."""
from __future__ import annotations

from pathlib import Path
from threading import Event, Lock, Thread
from typing import Callable

from PySide6.QtCore import QObject, QTimer, Signal

from frontengine.utils.todo.repository import TodoRepository, atomic_write
from frontengine.utils.todo.calendar_import import MAX_CALENDAR_BYTES


class TodoService(QObject):
    """Serialize explicit user operations; closing rejects results and pending writes."""

    result = Signal(str, object)
    failed = Signal(str, str)
    started = Signal(str)

    def __init__(self, path: str | Path, parent=None, *, writer: Callable = atomic_write) -> None:
        super().__init__(parent)
        self.path, self.writer = Path(path), writer
        self.items, self.busy, self.loaded = [], False, False
        self.cancelled, self.lock, self.mailbox = Event(), Lock(), None
        self.thread = None
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self._poll)

    def request(self, action: str, **arguments) -> bool:
        """Accept one job; never coalesce or silently replace user mutations."""
        fields = {'load': set(), 'add': {'title', 'due'}, 'done': {'id', 'value'},
                  'remove': {'id'}, 'import': {'path'}, 'clear': set()}
        if action not in fields or set(arguments) != fields[action]:
            raise ValueError('Invalid task service operation')
        if self.cancelled.is_set() or self.busy:
            return False
        self.busy = True
        self.started.emit(action)
        self.timer.start()
        self.thread = Thread(target=self._run, args=(action, dict(arguments)), name='FrontEngineTasks', daemon=True)
        self.thread.start()
        return True

    def _write(self, path: Path, data: bytes) -> None:
        if self.cancelled.is_set():
            raise ValueError('Task operation was cancelled before saving')
        self.writer(path, data)

    def _run(self, action: str, arguments: dict) -> None:
        try:
            repository = TodoRepository(self.path, writer=self._write)
            if action == 'import':
                with Path(arguments['path']).open('rb') as stream:
                    data = stream.read(MAX_CALENDAR_BYTES + 1)
                arguments = {'data': data}
            value = repository.snapshot() if action == 'load' else repository.apply(action, arguments)
            result = value, ''
        except Exception as error:
            result = None, str(error)[:2000]
        with self.lock:
            if not self.cancelled.is_set():
                self.mailbox = action, result

    def _poll(self) -> None:
        with self.lock:
            result, self.mailbox = self.mailbox, None
        if result is None:
            return
        self.busy = False
        self.timer.stop()
        action, (value, error) = result
        if error:
            self.failed.emit(action, error)
        else:
            self.items, self.loaded = value, True
            self.result.emit(action, value)

    def stop(self) -> None:
        """Drop results and prevent writes that have not started; do not wait on the GUI."""
        self.cancelled.set()
        self.timer.stop()
        with self.lock:
            self.mailbox = None
