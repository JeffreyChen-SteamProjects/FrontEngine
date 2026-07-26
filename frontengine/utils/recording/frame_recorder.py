"""
畫面錄製：定時抓一塊螢幕，存成一連串畫面，最後寫成動畫 GIF。可以把攝影機
畫面疊在角落（子母畫面），做成「反應影片」那種效果。

錄製有硬性上限（秒數與張數），因為每一張都留在記憶體裡——沒有上限的話，
錄久一點就會把記憶體吃光。

Frame recording: grab a region on a timer, keep the frames, and write them out
as an animated GIF. The camera can be composited into a corner for the
picture-in-picture "reaction" look.

Recording is hard-capped by seconds and frame count, because every frame is
held in memory - without a cap a long recording would simply exhaust it.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional

import numpy
from PySide6.QtCore import QObject, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication, QImage, QPainter, QPixmap

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.recording.gif_writer import encode_gif

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


def clamp_max_seconds(value, fallback: int = DEFAULT_MAX_SECONDS) -> int:
    """單次錄製長度夾在 1~120 秒。"""
    try:
        return max(1, min(120, int(value)))
    except (TypeError, ValueError):
        return fallback


def frame_budget(fps: int, max_seconds: int) -> int:
    """這次錄製最多可以留幾張（同時受總張數上限限制）。"""
    return max(1, min(MAX_FRAMES, clamp_fps(fps) * clamp_max_seconds(max_seconds)))


def image_to_rgb(image: QImage) -> Optional[numpy.ndarray]:
    """QImage -> H x W x 3 的 uint8 陣列（處理每列的補齊位元組）。"""
    if image is None or image.isNull():
        return None
    converted = image.convertToFormat(QImage.Format.Format_RGB888)
    width, height, stride = converted.width(), converted.height(), converted.bytesPerLine()
    if width <= 0 or height <= 0:
        return None
    buffer = numpy.frombuffer(converted.constBits(), dtype=numpy.uint8, count=stride * height)
    return buffer.reshape(height, stride)[:, : width * 3].reshape(height, width, 3).copy()


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
    """
    定時抓畫面並存起來。擷取函式與子母畫面來源都可注入，所以整個錄製流程
    不需要真的螢幕或攝影機也測得到。
    """

    finished = Signal(int)  # 錄到的張數 / how many frames were captured

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.frames: List[numpy.ndarray] = []
        self.fps = DEFAULT_FPS
        self.max_seconds = DEFAULT_MAX_SECONDS
        self.region = QRect()
        self._grabber: Callable[[QRect], Optional[QPixmap]] = self._default_grabber
        self._inset_provider: Optional[Callable[[], Optional[QPixmap]]] = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.capture_frame)

    @property
    def running(self) -> bool:
        return self._timer.isActive()

    @staticmethod
    def _default_grabber(rect: QRect) -> Optional[QPixmap]:  # pragma: no cover - real screen
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return None
        return screen.grabWindow(0, rect.x(), rect.y(), rect.width(), rect.height())

    def set_grabber(self, grabber) -> None:
        self._grabber = grabber or self._default_grabber

    def set_inset_provider(self, provider) -> None:
        """設定子母畫面來源（回傳 QPixmap 或 None）。"""
        self._inset_provider = provider

    def start(self, region: QRect, fps: int = DEFAULT_FPS,
              max_seconds: int = DEFAULT_MAX_SECONDS) -> bool:
        """開始錄製一塊區域；範圍無效時回傳 False。"""
        if region is None or region.width() <= 0 or region.height() <= 0:
            return False
        self.frames = []
        self.region = QRect(region)
        self.fps = clamp_fps(fps)
        self.max_seconds = clamp_max_seconds(max_seconds)
        front_engine_logger.info(
            f"[FrameRecorder] start | {self.region.width()}x{self.region.height()} "
            f"@{self.fps}fps, max {self.max_seconds}s")
        self.capture_frame()
        self._timer.start(max(1, 1000 // self.fps))
        return True

    def stop(self) -> int:
        """停止錄製並回傳張數。"""
        if self._timer.isActive():
            self._timer.stop()
            front_engine_logger.info(f"[FrameRecorder] stop | {len(self.frames)} frame(s)")
            self.finished.emit(len(self.frames))
        return len(self.frames)

    def capture_frame(self) -> bool:
        """抓一張（測試會直接呼叫）。到達張數上限時自動停止。"""
        if len(self.frames) >= frame_budget(self.fps, self.max_seconds):
            self.stop()
            return False
        try:
            pixmap = self._grabber(self.region)
        except Exception as error:  # pragma: no cover - screen grab boundary
            front_engine_logger.warning(f"[FrameRecorder] grab failed: {error!r}")
            return False
        if pixmap is None or pixmap.isNull():
            return False
        if self._inset_provider is not None:
            try:
                pixmap = composite_inset(pixmap, self._inset_provider())
            except Exception as error:  # pragma: no cover - defensive around providers
                front_engine_logger.debug(f"[FrameRecorder] inset failed: {error!r}")
        pixels = image_to_rgb(pixmap.toImage())
        if pixels is None:
            return False
        self.frames.append(pixels)
        if len(self.frames) >= frame_budget(self.fps, self.max_seconds):
            self.stop()
        return True

    def save_gif(self, path: str) -> Optional[str]:
        """
        把錄到的畫面寫成動畫 GIF，回傳實際路徑；沒有畫面就回傳 None。
        Write the frames out as an animated GIF and return the path; None when
        nothing was recorded.
        """
        if not self.frames:
            return None
        data = encode_gif(self.frames, delay_ms=max(20, 1000 // max(1, self.fps)))
        if data is None:
            return None
        target = Path(path)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        except OSError as error:
            front_engine_logger.warning(f"[FrameRecorder] save failed: {error!r}")
            return None
        front_engine_logger.info(f"[FrameRecorder] saved | {target} ({len(self.frames)} frames)")
        return str(target)

    def clear(self) -> None:
        """丟掉錄到的畫面（釋放記憶體）。"""
        self.frames = []
