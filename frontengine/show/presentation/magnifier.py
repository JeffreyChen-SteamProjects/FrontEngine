"""
區域放大鏡：抓取游標周圍的一小塊畫面，放大後顯示在覆蓋層上，
方便簡報時展示細節（ZoomIt 式）。點擊穿透，抓圖用 Qt 自己的螢幕擷取。

A region magnifier: grab a small area around the cursor and draw it enlarged,
for showing detail during a demo. Click-through, and the capture uses Qt's own
screen grab rather than any platform API.
"""
from __future__ import annotations

from typing import Optional, Tuple

from PySide6.QtCore import QPoint, QRect, QTimer, Qt
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QPainter, QPixmap

from frontengine.show.base_widget import BaseWidget
from frontengine.utils.logging.loggin_instance import front_engine_logger

MIN_ZOOM = 1.25
MAX_ZOOM = 8.0
DEFAULT_ZOOM = 2.0
DEFAULT_SIZE = 240


def clamp_zoom(value, fallback: float = DEFAULT_ZOOM) -> float:
    """把放大倍率夾在 1.25x~8x（再高就只剩馬賽克）。"""
    try:
        return max(MIN_ZOOM, min(MAX_ZOOM, round(float(value), 2)))
    except (TypeError, ValueError):
        return fallback


def source_rect(center: Tuple[int, int], size: int, zoom: float,
                bounds: Tuple[int, int, int, int]) -> QRect:
    """
    算出要擷取的螢幕區域：以游標為中心、邊長為顯示尺寸除以倍率，並限制在螢幕內。
    The screen area to grab: centred on the cursor, sized by the zoom factor,
    and kept inside the screen.
    """
    side = max(8, int(int(size) / max(MIN_ZOOM, float(zoom))))
    left, top, right, bottom = bounds
    x = int(center[0]) - side // 2
    y = int(center[1]) - side // 2
    x = max(left, min(x, max(left, right - side)))
    y = max(top, min(y, max(top, bottom - side)))
    return QRect(x, y, side, side)


class MagnifierWidget(BaseWidget):
    """
    放大鏡：定期擷取游標周圍畫面並放大顯示。擷取來源可注入，方便測試。
    """

    REFRESH_MS = 60

    def __init__(self, zoom: float = DEFAULT_ZOOM, size: int = DEFAULT_SIZE) -> None:
        front_engine_logger.info(f"[MagnifierWidget] Init | zoom={zoom}, size={size}")
        super().__init__()
        self.opacity = 1.0
        self.zoom = clamp_zoom(zoom)
        self.view_size = max(80, int(size))
        self.captured: Optional[QPixmap] = None
        self._cursor_provider = QCursor.pos
        self._grabber = self._grab_screen
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)

    def set_cursor_provider(self, provider) -> None:
        self._cursor_provider = provider

    def set_grabber(self, grabber) -> None:
        """注入擷取函式：接收 QRect，回傳 QPixmap（測試用）。"""
        self._grabber = grabber

    def set_zoom(self, zoom: Optional[float] = None, size: Optional[int] = None) -> None:
        if zoom is not None:
            self.zoom = clamp_zoom(zoom)
        if size is not None:
            self.view_size = max(80, int(size))
            self.resize(self.view_size, self.view_size)
        self.update()

    def start_following(self, interval_ms: int = REFRESH_MS) -> None:
        self.refresh()
        self._timer.start(max(16, int(interval_ms)))

    @staticmethod
    def _grab_screen(rect: QRect) -> Optional[QPixmap]:
        """用 Qt 擷取指定螢幕區域；沒有可用螢幕時回傳 None。"""
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return None
        return screen.grabWindow(0, rect.x(), rect.y(), rect.width(), rect.height())

    def screen_bounds(self) -> Tuple[int, int, int, int]:
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            return (0, 0, 1920, 1080)
        geometry = screen.geometry()
        return (geometry.left(), geometry.top(), geometry.right(), geometry.bottom())

    def refresh(self) -> None:
        """擷取游標周圍的畫面 / Grab the area around the cursor."""
        try:
            position = self._cursor_provider()
            rect = source_rect((position.x(), position.y()), self.view_size, self.zoom,
                               self.screen_bounds())
            self.captured = self._grabber(rect)
        except Exception as error:  # pragma: no cover - capture boundary
            front_engine_logger.debug(f"[MagnifierWidget] capture failed: {error!r}")
            return
        self.update()

    def draw_content(self, painter: QPainter) -> None:
        if self.captured is None or self.captured.isNull():
            return
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        target = QRect(0, 0, self.width(), self.height())
        painter.drawPixmap(target, self.captured)
        painter.setPen(QColor(255, 255, 255, 180))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(target.adjusted(0, 0, -1, -1))

    def closeEvent(self, event) -> None:
        if self._timer.isActive():
            self._timer.stop()
        super().closeEvent(event)
