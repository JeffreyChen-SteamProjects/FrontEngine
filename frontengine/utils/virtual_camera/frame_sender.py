"""One latest RGB frame and one device worker; never block the Qt GUI on send."""
from __future__ import annotations

from threading import Condition, Thread
from typing import Callable

import numpy
from PySide6.QtCore import QObject, Signal

from frontengine.utils.virtual_camera.virtual_camera import VirtualCameraOutput


class FrameSender(QObject):
    """Device ownership stays on its worker until close, including startup failure."""

    ready = Signal(str)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, width: int, height: int, fps: int, parent=None,
                 *, factory: Callable = VirtualCameraOutput) -> None:
        super().__init__(parent)
        if any(type(value) is not int or value < 2 or value % 2 for value in (width, height)) or width * height > 1920 * 1080:
            raise ValueError('Virtual camera dimensions must be even and within 1920×1080 pixels')
        self.width, self.height, self.fps, self.factory = width, height, fps, factory
        self.condition = Condition()
        self.pending = None
        self.stopping = False
        self.frames = self.dropped = 0
        self.thread = Thread(target=self._run, daemon=True)

    def start(self) -> None:
        """Open the device on its worker; ready/failure delivery is asynchronous."""
        self.thread.start()

    def submit(self, pixels: numpy.ndarray) -> bool:
        """Transfer a detached bounded RGB array, replacing any pending frame."""
        if pixels.dtype != numpy.uint8 or pixels.shape != (self.height, self.width, 3):
            raise ValueError('Virtual camera frame does not match the fixed RGB size')
        with self.condition:
            if self.stopping:
                return False
            if self.pending is not None:
                self.dropped += 1
            self.pending = pixels
            self.condition.notify()
        return True

    def stop(self) -> None:
        """Request disposal without waiting for device work on the GUI thread."""
        with self.condition:
            self.stopping = True
            self.pending = None
            self.condition.notify()

    def _emit(self, signal, *args) -> None:
        try:
            signal.emit(*args)
        except RuntimeError:
            pass  # Device cleanup still runs after the QObject owner is deleted.

    def _run(self) -> None:
        output = None
        try:
            if self.stopping:
                return
            output = self.factory(self.width, self.height, self.fps)
            if not output.start():
                raise RuntimeError(output.last_error)
            self._emit(self.ready, output.device)
            self._send(output)
        except (OSError, ValueError, RuntimeError) as error:
            self._emit(self.failed, str(error))
        finally:
            if output is not None:
                output.stop()
            self.stop()
            self._emit(self.finished)

    def _send(self, output) -> None:
        while True:
            with self.condition:
                self.condition.wait_for(lambda: self.pending is not None or self.stopping)
                if self.stopping:
                    return
                pixels, self.pending = self.pending, None
            if not output.send(pixels):
                raise RuntimeError(output.last_error or 'Virtual camera could not send a frame')
            self.frames += 1
