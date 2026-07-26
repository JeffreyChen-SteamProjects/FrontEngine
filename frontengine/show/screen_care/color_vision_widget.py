"""
色覺模擬覆蓋層：抓一張畫面、套上色覺缺陷的轉換、再整片蓋回去。

這一層和其他覆蓋層不同：它必須是不透明的，因為「模擬看不清楚的顏色」沒辦法
用半透明疊色做到——得真的把底下的畫面重畫一次。畫面只在記憶體裡轉換，不存檔。

A colour-vision overlay: grab the screen, apply the deficiency transform, and
paint the result back over everything.

It is opaque, unlike the other overlays: simulating a colour deficiency cannot
be done by tinting, it needs the picture underneath redrawn. The grab is
transformed in memory and never saved.
"""
from __future__ import annotations

from typing import Optional

import numpy
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication, QImage, QPainter, QPixmap

from frontengine.show.base_widget import BaseWidget
from frontengine.utils.color_vision.color_vision import (
    KIND_DEUTERANOPIA, clamp_severity, normalize_kind, simulate_array,
)
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.power_mode.power_mode import tier_interval

# 色覺模擬不需要很高的更新率，五分之一秒足夠，也省下大量重繪
# The simulation does not need a high refresh rate; five per second is plenty
# and saves a great deal of redrawing.
REFRESH_INTERVAL_MS = 200


def image_to_array(image: QImage) -> Optional[numpy.ndarray]:
    """
    QImage -> H x W x 3 的 uint8 陣列。每列可能有補齊位元組，所以要照
    bytesPerLine 切，不能直接 reshape。
    QImage to an H x W x 3 uint8 array. Rows can be padded, so slice by
    bytesPerLine rather than reshaping the raw buffer.
    """
    if image is None or image.isNull():
        return None
    converted = image.convertToFormat(QImage.Format.Format_RGB888)
    width, height, stride = converted.width(), converted.height(), converted.bytesPerLine()
    if width <= 0 or height <= 0:
        return None
    buffer = numpy.frombuffer(converted.constBits(), dtype=numpy.uint8, count=stride * height)
    return buffer.reshape((height, stride))[:, : width * 3].reshape(
        (height, width, 3)).copy()


def array_to_image(pixels: numpy.ndarray) -> Optional[QImage]:
    """H x W x 3 的 uint8 陣列 -> QImage（複製一份，不依賴呼叫端的緩衝區）。"""
    data = numpy.ascontiguousarray(pixels, dtype=numpy.uint8)
    if data.ndim != 3 or data.shape[2] != 3:
        return None
    height, width, _channels = data.shape
    image = QImage(data.tobytes(), width, height, width * 3, QImage.Format.Format_RGB888)
    return image.copy()


class ColorVisionWidget(BaseWidget):
    """
    色覺模擬層。擷取函式可注入，所以不需要真的螢幕也測得到轉換流程。
    """

    def __init__(self, kind: str = KIND_DEUTERANOPIA, severity: float = 1.0) -> None:
        front_engine_logger.info(f"[ColorVisionWidget] Init | kind={kind}")
        super().__init__()
        self.kind = normalize_kind(kind)
        self.severity = clamp_severity(severity)
        self.opacity = 1.0
        self.simulated: Optional[QPixmap] = None
        self._grabber = self._default_grabber
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        # 這一層是不透明的：它要蓋掉底下的畫面，而不是疊在上面
        # This layer is opaque - it replaces what is underneath rather than
        # tinting it.
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

    @staticmethod
    def _default_grabber(rect):  # pragma: no cover - needs a real screen
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return None
        return screen.grabWindow(0, rect.x(), rect.y(), rect.width(), rect.height())

    def set_grabber(self, grabber) -> None:
        """設定螢幕擷取函式（測試會換成假的）。"""
        self._grabber = grabber or self._default_grabber

    def set_simulation(self, kind: Optional[str] = None,
                       severity: Optional[float] = None) -> None:
        """換一種色覺類型或嚴重程度，立刻重畫。"""
        if kind is not None:
            self.kind = normalize_kind(kind)
        if severity is not None:
            self.severity = clamp_severity(severity)
        self.refresh()

    def start(self) -> None:
        self.refresh()
        self._timer.start(tier_interval(REFRESH_INTERVAL_MS, self.quality_tier))

    def stop(self) -> None:
        self._timer.stop()

    def apply_quality_tier(self) -> None:
        if self._timer.isActive():
            self._timer.start(tier_interval(REFRESH_INTERVAL_MS, self.quality_tier))

    def refresh(self) -> None:
        """抓一次畫面、轉換、準備重畫。"""
        geometry = self.geometry()
        try:
            # 擷取時先把自己藏起來，否則會拍到上一次的模擬結果，越疊越糊
            # Hide first, or the grab catches the previous simulation and the
            # picture degrades with every pass.
            was_visible = self.isVisible()
            if was_visible:
                self.setVisible(False)
            pixmap = self._grabber(geometry)
            if was_visible:
                self.setVisible(True)
        except Exception as error:  # pragma: no cover - screen grab boundary
            front_engine_logger.warning(f"[ColorVisionWidget] grab failed: {error!r}")
            return
        if pixmap is None or pixmap.isNull():
            return
        pixels = image_to_array(pixmap.toImage())
        if pixels is None:
            return
        image = array_to_image(simulate_array(pixels, self.kind, self.severity))
        if image is not None:
            self.simulated = QPixmap.fromImage(image)
            self.update()

    def draw_content(self, painter: QPainter) -> None:
        if self.simulated is None or self.simulated.isNull():
            return
        painter.drawPixmap(self.rect(), self.simulated)

    def closeEvent(self, event) -> None:
        self.stop()
        super().closeEvent(event)
