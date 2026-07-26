"""
量測覆蓋層：取色器、像素尺、量角器。三個模式共用同一層全螢幕覆蓋，
因為它們都要「看得到螢幕內容、也收得到滑鼠」。

The measuring overlay: colour picker, pixel ruler and protractor. All three
share one fullscreen layer, because all three need to see what is on screen and
to receive the mouse.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen

from frontengine.show.base_widget import BaseWidget
from frontengine.show.window_helpers import apply_overlay_window_flags
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.measure.measure import (
    FORMAT_HEX, angle_at, format_color, measurement_text,
)

MODE_COLOR = "color"
MODE_RULER = "ruler"
MODE_ANGLE = "angle"
MODES = (MODE_COLOR, MODE_RULER, MODE_ANGLE)

_SWATCH_SIZE = 96
_LABEL_PADDING = 8
_LINE_COLOR = "#ff5252"


def normalize_mode(mode) -> str:
    """把模式正規化；不認得的一律當取色器。"""
    name = str(mode or "").strip().lower()
    return name if name in MODES else MODE_COLOR


def grab_pixel_color(grabber, point: QPoint) -> Optional[QColor]:
    """
    抓游標所在那一個像素的顏色；抓不到（無畫面、擷取失敗）回傳 None。
    The colour of the pixel under the cursor, or None when the screen cannot be
    grabbed at all.
    """
    try:
        pixmap = grabber(QRect(point.x(), point.y(), 1, 1))
    except Exception as error:  # pragma: no cover - screen grab boundary
        front_engine_logger.debug(f"[MeasureWidget] pixel grab failed: {error!r}")
        return None
    if pixmap is None or pixmap.isNull():
        return None
    image = pixmap.toImage()
    if image.isNull():
        return None
    return image.pixelColor(0, 0)


class MeasureWidget(BaseWidget):
    """
    量測覆蓋層。螢幕擷取函式可注入（測試用假的），所以整個互動流程都測得到。
    """

    def __init__(self, mode: str = MODE_COLOR, color_format: str = FORMAT_HEX) -> None:
        front_engine_logger.info(f"[MeasureWidget] Init | mode={mode}")
        super().__init__()
        self.mode = normalize_mode(mode)
        self.color_format = color_format
        self.opacity = 1.0
        self.overlay_lockable = False
        self.points: List[QPoint] = []
        self.cursor_point = QPoint(0, 0)
        self.picked_color: Optional[QColor] = None
        self.readout: str = ""
        self._grabber = self._default_grabber
        self._font = QFont()
        self._font.setPointSize(11)
        apply_overlay_window_flags(self, show_on_bottom=False, allow_input=True)
        self.setCursor(Qt.CursorShape.CrossCursor)

    @staticmethod
    def _default_grabber(rect: QRect):
        screen = QGuiApplication.primaryScreen()
        if screen is None:  # pragma: no cover - no screen at all
            return None
        return screen.grabWindow(0, rect.x(), rect.y(), rect.width(), rect.height())

    def set_grabber(self, grabber) -> None:
        """設定螢幕擷取函式（測試會換成假的）。"""
        self._grabber = grabber or self._default_grabber

    def set_mode(self, mode: str) -> None:
        """換模式並清掉上一輪的量測。"""
        self.mode = normalize_mode(mode)
        self.reset()

    def set_color_format(self, color_format: str) -> None:
        self.color_format = color_format
        if self.picked_color is not None:
            self.readout = self.color_text(self.picked_color)
        self.update()

    def reset(self) -> None:
        self.points.clear()
        self.picked_color = None
        self.readout = ""
        self.update()

    def color_text(self, color: QColor) -> str:
        """把顏色排成使用者選的格式。"""
        return format_color((color.red(), color.green(), color.blue()), self.color_format)

    # --- interaction -----------------------------------------------------
    def track_cursor(self, point: QPoint) -> None:
        """游標移動：取色模式會即時更新色塊。"""
        self.cursor_point = QPoint(point)
        if self.mode == MODE_COLOR:
            color = grab_pixel_color(self._grabber, point)
            if color is not None:
                self.picked_color = color
                self.readout = self.color_text(color)
        elif self.mode == MODE_RULER and len(self.points) == 1:
            self.readout = measurement_text(
                (self.points[0].x(), self.points[0].y()), (point.x(), point.y()))
        self.update()

    def add_point(self, point: QPoint) -> Optional[str]:
        """
        按下一點。尺需要兩點、量角器需要三點，湊齊時回傳要顯示（並複製）的
        文字，還沒湊齊回傳 None。
        Add a click. The ruler wants two points and the protractor three; the
        text to show - and copy - comes back once there are enough.
        """
        if self.mode == MODE_COLOR:
            color = grab_pixel_color(self._grabber, point)
            if color is None:
                return None
            self.picked_color = color
            self.readout = self.color_text(color)
            self.update()
            return self.readout
        self.points.append(QPoint(point))
        needed = 2 if self.mode == MODE_RULER else 3
        if len(self.points) < needed:
            self.update()
            return None
        self.readout = self._finish_measurement()
        self.points = self.points[:needed]
        self.update()
        return self.readout

    def _finish_measurement(self) -> str:
        if self.mode == MODE_RULER:
            start, end = self.points[0], self.points[1]
            return measurement_text((start.x(), start.y()), (end.x(), end.y()))
        first, vertex, second = self.points[0], self.points[1], self.points[2]
        degrees = angle_at((vertex.x(), vertex.y()), (first.x(), first.y()),
                           (second.x(), second.y()))
        return f"{degrees:.1f}°"

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            copied = self.add_point(event.position().toPoint())
            if copied:
                self.copy_to_clipboard(copied)
        elif event.button() == Qt.MouseButton.RightButton:
            self.reset()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        self.track_cursor(event.position().toPoint())
        super().mouseMoveEvent(event)

    @staticmethod
    def copy_to_clipboard(text: str) -> bool:
        """把量測結果放到剪貼簿；沒有剪貼簿時回傳 False。"""
        clipboard = QGuiApplication.clipboard()
        if clipboard is None:  # pragma: no cover - no clipboard at all
            return False
        clipboard.setText(str(text))
        front_engine_logger.info(f"[MeasureWidget] copied | {text}")
        return True

    # --- painting --------------------------------------------------------
    def draw_content(self, painter: QPainter) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self.mode == MODE_COLOR:
            self._draw_swatch(painter)
        else:
            self._draw_measurement(painter)
        if self.readout:
            self._draw_readout(painter)

    def _draw_swatch(self, painter: QPainter) -> None:
        if self.picked_color is None:
            return
        origin = self._readout_origin()
        rect = QRect(origin[0], origin[1] - _SWATCH_SIZE - _LABEL_PADDING,
                     _SWATCH_SIZE, _SWATCH_SIZE)
        painter.fillRect(rect, self.picked_color)
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.drawRect(rect)

    def _draw_measurement(self, painter: QPainter) -> None:
        pen = QPen(QColor(_LINE_COLOR), 2)
        painter.setPen(pen)
        points = list(self.points)
        if self.mode == MODE_RULER and len(points) == 1:
            points.append(self.cursor_point)
        for index in range(1, len(points)):
            painter.drawLine(points[index - 1], points[index])
        for point in points:
            painter.drawEllipse(point, 4, 4)

    def _draw_readout(self, painter: QPainter) -> None:
        painter.setFont(self._font)
        origin = self._readout_origin()
        text_rect = QRect(origin[0], origin[1], 220, 28)
        painter.fillRect(text_rect, QColor(20, 20, 20, 220))
        painter.setPen(QColor("#ffffff"))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.readout)

    def _readout_origin(self) -> Tuple[int, int]:
        """把讀數放在游標旁邊，靠近邊緣時往內收。"""
        x = min(max(0, self.cursor_point.x() + 16), max(0, self.width() - 230))
        y = min(max(_SWATCH_SIZE + _LABEL_PADDING, self.cursor_point.y() + 16),
                max(0, self.height() - 30))
        return (x, y)
