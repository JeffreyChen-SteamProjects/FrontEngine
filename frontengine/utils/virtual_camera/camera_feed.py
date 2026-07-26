"""
把螢幕上的一塊畫面持續餵給虛擬攝影機。抓畫面的方式和錄影完全一樣，
所以覆蓋層本來長什麼樣，對方看到的就是什麼樣。

Keep feeding a region of the screen to the virtual camera. It grabs exactly the
way the recorder does, so whatever the overlays look like here is what the other
side sees.
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QObject, QRect, QTimer, Signal
from PySide6.QtGui import QGuiApplication, QPixmap

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.recording.frame_recorder import image_to_rgb
from frontengine.utils.virtual_camera.virtual_camera import VirtualCameraOutput, clamp_fps


class VirtualCameraFeed(QObject):
    """
    定時抓一塊螢幕送進虛擬攝影機。擷取函式可注入，所以整條流程不需要真的
    螢幕也測得到。
    """

    failed = Signal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.output: Optional[VirtualCameraOutput] = None
        self.region = QRect()
        self.frames = 0
        self._grabber: Callable[[QRect], Optional[QPixmap]] = self._default_grabber
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.send_frame)

    @property
    def running(self) -> bool:
        return self.output is not None and self.output.running

    @staticmethod
    def _default_grabber(rect: QRect) -> Optional[QPixmap]:  # pragma: no cover - real screen
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return None
        return screen.grabWindow(0, rect.x(), rect.y(), rect.width(), rect.height())

    def set_grabber(self, grabber) -> None:
        self._grabber = grabber or self._default_grabber

    def start(self, region: QRect, fps: int) -> bool:
        """
        開始輸出。範圍無效、沒有套件或沒有驅動都會回傳 False，並把原因
        透過 failed 訊號說出來。
        Start feeding. An invalid region, a missing package or a missing driver
        all return False, with the reason reported through failed.
        """
        if self.running:
            return True
        if region is None or region.width() <= 0 or region.height() <= 0:
            self.failed.emit("invalid region")
            return False
        self.region = QRect(region)
        self.output = VirtualCameraOutput(region.width(), region.height(), clamp_fps(fps))
        if not self.output.start():
            reason = self.output.last_error
            self.output = None
            self.failed.emit(reason)
            return False
        self.frames = 0
        self._timer.start(max(1, 1000 // clamp_fps(fps)))
        front_engine_logger.info("[VirtualCameraFeed] start")
        return True

    def stop(self) -> None:
        """停止輸出並關掉攝影機。"""
        self._timer.stop()
        if self.output is not None:
            self.output.stop()
            self.output = None
        front_engine_logger.info(f"[VirtualCameraFeed] stop after {self.frames} frame(s)")

    def send_frame(self) -> bool:
        """抓一張並送出（測試會直接呼叫）。"""
        if self.output is None:
            return False
        try:
            pixmap = self._grabber(self.region)
        except Exception as error:  # pragma: no cover - screen grab boundary
            front_engine_logger.warning(f"[VirtualCameraFeed] grab failed: {error!r}")
            return False
        if pixmap is None or pixmap.isNull():
            return False
        pixels = image_to_rgb(pixmap.toImage())
        if pixels is None or not self.output.send(pixels):
            return False
        self.frames += 1
        return True

    def device_name(self) -> str:
        """目前輸出到哪一支虛擬攝影機。"""
        return self.output.device if self.output is not None else ""
