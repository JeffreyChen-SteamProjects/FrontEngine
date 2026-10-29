"""GUI capture ownership and one detached, cancellable-result OCR job per window."""
from __future__ import annotations

import sys
from threading import Event, Lock, Thread
from typing import Callable

from PySide6.QtCore import QObject, QRect, QTimer, Qt, Signal
from PySide6.QtGui import QGuiApplication, QImage

from frontengine.utils.image_history.repository import encode_image
from frontengine.utils.screen_text.screen_text_service import ScreenTextResult


def make_live_reader(service) -> Callable[[bytes, bool], ScreenTextResult]:
    """Keep local-only mode separate even when existing global cloud consent is enabled."""
    def read(data: bytes, cloud: bool) -> ScreenTextResult:
        if cloud:
            return service.read_result(data)
        result = service.local_backend.recognize(data)
        return ScreenTextResult(result.status, result.text, result.backend, result.error)
    return read


class RegionSource(QObject):
    """Capture one bounded screen-local Qt region, or an asynchronous native Mac region."""

    frame = Signal(QImage)
    failed = Signal(str)

    def __init__(self, parent=None, *, native_factory=None, screen_provider=QGuiApplication.screenAt) -> None:
        super().__init__(parent)
        self.native_factory, self.screen_provider = native_factory, screen_provider
        self.native, self.polls = None, 0
        self.timer = QTimer(self)
        self.timer.setInterval(30)
        self.timer.timeout.connect(self._poll)

    def start(self, region: QRect) -> None:
        """Start only after explicit refresh; stop native streaming after one available frame."""
        self.stop()
        if region.width() < 4 or region.height() < 4 or region.width()*region.height() > 16_777_216:
            self.failed.emit('OCR region must be 4×4 pixels or larger and within 16 megapixels')
            return
        if sys.platform == 'darwin' or self.native_factory is not None:
            if self.native is None:
                from frontengine.utils.macos.region_capture import RegionCaptureAdapter
                self.native = (self.native_factory or RegionCaptureAdapter)(self)
                self.native.failed.connect(self._failed, Qt.ConnectionType.QueuedConnection)
            if not self.native.start(region):
                self._failed('Native region capture could not start; check Screen Recording permission')
            else:
                self.polls = 0
                self.timer.start()
            return
        screen = self.screen_provider(region.center())
        if screen is None or not screen.geometry().contains(region):
            self.failed.emit('OCR region must fit within one available screen')
            return
        origin = region.topLeft()-screen.geometry().topLeft()
        pixmap = screen.grabWindow(0, origin.x(), origin.y(), region.width(), region.height())
        if pixmap.isNull():
            self.failed.emit('Screen capture unavailable; check desktop capture permissions')
        else:
            self.frame.emit(pixmap.toImage())

    def _poll(self) -> None:
        self.polls += 1
        pixmap = self.native.latest_frame()
        if pixmap is not None and not pixmap.isNull():
            image = pixmap.toImage()
            self.stop()
            self.frame.emit(image)
        elif self.polls >= 167:
            self._failed('Native region capture timed out; check Screen Recording permission')

    def _failed(self, reason: str) -> None:
        self.stop()
        self.failed.emit(reason)

    def stop(self) -> None:
        """Cancel polls and release native capture when hidden, closed or a frame arrives."""
        self.timer.stop()
        if self.native is not None:
            self.native.stop()


class LiveOcrSession(QObject):
    """Poll one worker result on GUI; close ignores late OCR/cloud completion."""

    completed = Signal(object)

    def __init__(self, reader: Callable[[bytes, bool], ScreenTextResult], parent=None) -> None:
        super().__init__(parent)
        self.reader, self.closed, self.busy = reader, Event(), False
        self.lock, self.result = Lock(), None
        self.thread = None
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self._poll)

    def submit(self, image: QImage, *, cloud: bool = False) -> bool:
        """Detach at most one input; never create a backlog of repeated timer requests."""
        if self.closed.is_set() or self.busy:
            return False
        self.busy = True
        detached = image.copy()
        self.thread = Thread(target=self._run, args=(detached, cloud), name='FrontEngineLiveOCR', daemon=True)
        self.thread.start()
        self.timer.start()
        return True

    def _run(self, image: QImage, cloud: bool) -> None:
        try:
            result = self.reader(encode_image(image), cloud)
            if not isinstance(result, ScreenTextResult) or not isinstance(result.text, str) or len(result.text) > 20000:
                raise ValueError('OCR must return a bounded ScreenTextResult')
        except Exception as error:
            result = ScreenTextResult('error', error=str(error)[:2000])
        with self.lock:
            if not self.closed.is_set():
                self.result = result

    def _poll(self) -> None:
        with self.lock:
            result, self.result = self.result, None
        if result is not None:
            self.busy = False
            self.timer.stop()
            self.completed.emit(result)

    def close(self) -> None:
        """Stop result polling without blocking GUI on an external OCR/API request."""
        self.closed.set()
        self.timer.stop()
        with self.lock:
            self.result = None
