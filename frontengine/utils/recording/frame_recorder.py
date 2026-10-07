"""GUI-thread region capture with bounded asynchronous GIF/AVI output."""
from __future__ import annotations

import time
import sys
from pathlib import Path
from typing import Callable, Optional

import numpy
from PySide6.QtCore import QObject, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication, QImage, QPainter, QPixmap

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.recording.gif_writer import (
    AsyncGifWriter, IncrementalGifWriter, MAX_QUEUED_BYTES,
)
from frontengine.utils.recording.avi_writer import IncrementalAviWriter, MAX_AVI_SECONDS, MAX_AVI_FRAMES

DEFAULT_FPS = 8
MIN_FPS = 1
MAX_FPS = 20
DEFAULT_MAX_SECONDS = 30
MAX_FRAMES = 600
# 子母畫面佔錄製範圍寬度的比例，以及離邊角的距離
# How much of the width the inset takes, and how far it sits from the corner.
_INSET_SHARE = 0.25
_INSET_MARGIN = 12


def clamp_fps(value, fallback: int = DEFAULT_FPS) -> int:
    """每秒張數夾在能實際做到的範圍。"""
    try:
        return max(MIN_FPS, min(MAX_FPS, int(value)))
    except (TypeError, ValueError):
        return fallback


def clamp_max_seconds(value, fallback: int = DEFAULT_MAX_SECONDS, maximum: int = 120) -> int:
    """單次錄製長度夾在 1~120 秒。"""
    try:
        return max(1, min(maximum, int(value)))
    except (TypeError, ValueError):
        return fallback


def frame_budget(fps: int, max_seconds: int, *, video: bool = False) -> int:
    """這次錄製最多可以留幾張（同時受總張數上限限制）。"""
    limit = MAX_AVI_FRAMES if video else MAX_FRAMES
    seconds = clamp_max_seconds(max_seconds, maximum=MAX_AVI_SECONDS if video else 120)
    return max(1, min(limit, clamp_fps(fps) * seconds))


def image_to_rgb(image: QImage) -> Optional[numpy.ndarray]:
    """QImage -> H x W x 3 的 uint8 陣列（處理每列的補齊位元組）。"""
    if image is None or image.isNull():
        return None
    converted = image.convertToFormat(QImage.Format.Format_RGB888)
    width, height, stride = converted.width(), converted.height(), converted.bytesPerLine()
    if width <= 0 or height <= 0:
        return None
    buffer = numpy.frombuffer(converted.constBits(), dtype=numpy.uint8, count=stride * height)
    return buffer.reshape((height, stride))[:, : width * 3].reshape(
        (height, width, 3)).copy()


def composite_inset(base: QPixmap, inset: Optional[QPixmap]) -> QPixmap:
    """
    把攝影機畫面縮小疊在右下角。沒有攝影機畫面就原樣回傳。
    Draw the camera into the bottom-right corner; without one, hand the frame
    straight back.
    """
    if inset is None or inset.isNull() or base.isNull():
        return base
    width = max(1, int(base.width() * _INSET_SHARE))
    scaled = inset.scaledToWidth(width, Qt.TransformationMode.SmoothTransformation)
    result = QPixmap(base)
    painter = QPainter(result)
    painter.drawPixmap(result.width() - scaled.width() - _INSET_MARGIN,
                       result.height() - scaled.height() - _INSET_MARGIN, scaled)
    painter.end()
    return result


class FrameRecorder(QObject):
    """Capture Qt images on the GUI thread; encode copied RGB on a worker."""

    finished = Signal(int)
    completed = Signal(object)
    failed = Signal(str)
    state_changed = Signal(str)
    progress = Signal(int, float, int)
    _writer_done = Signal(object, object, object)

    def __init__(self, parent: Optional[QObject] = None,
                 writer_factory: Callable = IncrementalGifWriter,
                 clock: Callable[[], float] = time.monotonic,
                 native_capture_factory: Optional[Callable] = None) -> None:
        super().__init__(parent)
        self.frame_count = 0
        self.dropped_frames = 0
        self.result_path: Optional[str] = None
        self.fps = DEFAULT_FPS
        self.max_seconds = DEFAULT_MAX_SECONDS
        self.region = QRect()
        self._grabber = self._default_grabber
        self._custom_grabber = False
        self._native_capture_factory = native_capture_factory
        self._native_capture = None
        self._inset_provider = None
        self._writer = None
        self._destroy_cleanup = None
        self._writer_factory = writer_factory
        self._clock = clock
        self._started_at = 0.0
        self._paused_at = None
        self._paused_duration = 0.0
        self._elapsed = 0.0
        self.state = 'idle'
        self.output_format = 'gif'
        self._attempts = 0
        self._capture_error = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.capture_frame)
        self._writer_done.connect(self._on_writer_done, Qt.ConnectionType.QueuedConnection)
        application = QGuiApplication.instance()
        if application is not None:
            application.aboutToQuit.connect(self.close)

    @property
    def running(self) -> bool:
        return self._timer.isActive()

    @property
    def busy(self) -> bool:
        return self._writer is not None

    @property
    def queued_frames(self) -> int:
        return self._writer.queued_frames if self._writer else 0

    @property
    def queued_bytes(self) -> int:
        return self._writer.queued_bytes if self._writer else 0

    @staticmethod
    def _default_grabber(rect: QRect) -> Optional[QPixmap]:  # pragma: no cover
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return None
        return screen.grabWindow(0, rect.x(), rect.y(), rect.width(), rect.height())

    def set_grabber(self, grabber: Optional[Callable]) -> None:
        self._grabber = grabber or self._default_grabber
        self._custom_grabber = grabber is not None

    def set_inset_provider(self, provider: Optional[Callable]) -> None:
        self._inset_provider = provider

    @property
    def elapsed_seconds(self) -> float:
        """Captured duration excludes pauses and remains fixed after stop."""
        return self._elapsed

    def _set_state(self, state: str) -> None:
        self.state = state
        self.state_changed.emit(state)

    def _effective_stamp(self) -> float:
        now = self._clock() if self._paused_at is None else self._paused_at
        return now - self._paused_duration

    def pause(self) -> bool:
        """Stop region capture without finalizing; exclude paused wall time."""
        if self.state != 'recording':
            return False
        self._paused_at = self._clock()
        self._elapsed = max(0, self._effective_stamp() - self._started_at)
        self._timer.stop()
        self._stop_native_capture()
        self._set_state('paused')
        self.progress.emit(self.frame_count, self._elapsed, self.dropped_frames)
        return True

    def resume(self) -> bool:
        """Resume the same clip and effective monotonic timeline."""
        if self.state != 'paused':
            return False
        if not self._start_native_capture():
            self._capture_error = 'Native capture could not resume'
            self.close()
            return False
        self._paused_duration += self._clock() - self._paused_at
        self._paused_at = None
        self._set_state('recording')
        self._timer.start(max(1, 1000 // self.fps))
        self.capture_frame()
        return True

    def start(self, region: QRect, target: Optional[str | Path] = None, fps: int = DEFAULT_FPS,
              max_seconds: int = DEFAULT_MAX_SECONDS, *, output_format: str | None = None) -> bool:
        if self.busy or not target or region is None:
            return False
        width, height = region.width(), region.height()
        if width <= 0 or height <= 0:
            return False
        if width > 65535 or height > 65535 or width * height * 3 > MAX_QUEUED_BYTES:
            self.failed.emit("Selected region exceeds the 64 MiB frame limit")
            return False
        self.output_format = output_format or ('avi' if Path(target).suffix.lower() == '.avi' else 'gif')
        if self.output_format not in ('gif', 'avi'):
            self.failed.emit('Unsupported recording format')
            return False
        self.frame_count = self.dropped_frames = self._attempts = 0
        self.result_path = None
        self._capture_error = None
        self.region = QRect(region)
        self.fps = clamp_fps(fps)
        self.max_seconds = clamp_max_seconds(max_seconds, maximum=MAX_AVI_SECONDS if self.output_format == 'avi' else 120)
        self._started_at = self._clock()
        self._paused_at, self._paused_duration, self._elapsed = None, 0.0, 0.0
        if not self._start_native_capture():
            return False
        factory = IncrementalAviWriter if self.output_format == 'avi' else self._writer_factory
        self._writer = AsyncGifWriter(target, delay_ms=1000 // self.fps,
                                      callback=self._notify_done,
                                      writer_factory=factory)
        # Destruction must cancel independently of the Python QObject wrapper.
        worker = self._writer
        self._destroy_cleanup = lambda *_args: worker.cancel()
        self.destroyed.connect(self._destroy_cleanup)
        self._set_state('recording')
        self._timer.start(max(1, 1000 // self.fps))
        self.capture_frame()
        return True

    def stop(self) -> int:
        self._stop_native_capture()
        if self.state in ('recording', 'paused') and self._writer is not None:
            self._timer.stop()
            stamp = self._effective_stamp()
            self._elapsed = max(0, stamp - self._started_at)
            self._set_state('finalizing')
            self._writer.stop(stamp)
            self.finished.emit(self.frame_count)
        return self.frame_count

    def close(self) -> None:
        """Cancel outstanding work without waiting for a slow encoder or disk."""
        self._timer.stop()
        self._stop_native_capture()
        if self._writer is not None:
            self._set_state('cancelling')
            self._writer.cancel()

    def clear(self) -> None:
        self.close()

    def _start_native_capture(self) -> bool:
        if self._custom_grabber or (sys.platform != 'darwin' and self._native_capture_factory is None):
            return True
        if self._native_capture is None:
            factory = self._native_capture_factory
            if factory is None:
                from frontengine.utils.macos.region_capture import RegionCaptureAdapter
                factory = RegionCaptureAdapter
            self._native_capture = factory(self)
            self._native_capture.failed.connect(self._native_capture_failed, Qt.ConnectionType.QueuedConnection)
            source = self._native_capture
            self.destroyed.connect(lambda *_args: source.stop())
        self._grabber = self._native_capture.latest_frame
        if self._native_capture.start(self.region):
            return True
        self.failed.emit('Native capture could not start. Check Screen Recording permissions.')
        return False

    def _stop_native_capture(self) -> None:
        if self._native_capture is not None:
            self._native_capture.stop()

    def _native_capture_failed(self, reason: str) -> None:
        if self.busy:
            self._capture_error = reason
            self.close()

    def capture_frame(self) -> bool:
        if not self.running:
            return False
        stamp = self._effective_stamp()
        self._elapsed = max(0, stamp - self._started_at)
        budget = frame_budget(self.fps, self.max_seconds, video=self.output_format == 'avi')
        if (stamp - self._started_at >= self.max_seconds
                or self._attempts >= budget):
            self.stop()
            return False
        self._attempts += 1
        if not self._writer.can_accept(self.region.width() * self.region.height() * 3):
            self.dropped_frames += 1
            captured = False
        else:
            captured = self._capture(stamp)
        self.progress.emit(self.frame_count, self._elapsed, self.dropped_frames)
        if self._attempts >= budget:
            self.stop()
        return captured

    def _capture(self, timestamp: float) -> bool:
        try:
            pixmap = self._grabber(self.region)
            if pixmap is None or pixmap.isNull():
                return False
            if pixmap.width() * pixmap.height() * 3 > MAX_QUEUED_BYTES:
                self._capture_error = "Captured frame exceeds the 64 MiB frame limit"
                self.close()
                return False
            if self._inset_provider is not None:
                try:
                    pixmap = composite_inset(pixmap, self._inset_provider())
                except Exception as error:
                    front_engine_logger.debug(f"[FrameRecorder] inset failed: {error!r}")
            pixels = image_to_rgb(pixmap.toImage())
            if pixels is None:
                return False
            if not self._writer.submit(pixels, timestamp):
                self.dropped_frames += 1
                return False
            self.frame_count += 1
            return True
        except Exception as error:
            front_engine_logger.warning(f"[FrameRecorder] grab failed: {error!r}")
            return False

    def _notify_done(self, writer, result, error) -> None:
        try:
            self._writer_done.emit(writer, result, error)
        except RuntimeError:
            pass  # The owning window has already been destroyed.

    def _on_writer_done(self, writer, result, error) -> None:
        if writer is not self._writer:
            return
        self._timer.stop()
        self._stop_native_capture()
        self.destroyed.disconnect(self._destroy_cleanup)
        self._destroy_cleanup = None
        self._writer = None
        self._set_state('idle')
        self.result_path = result
        error = error or self._capture_error
        if error:
            self.failed.emit(error)
        else:
            self.completed.emit(result)
