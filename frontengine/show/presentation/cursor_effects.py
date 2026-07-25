"""
游標強調層：在游標周圍畫一圈亮環、點擊時擴散漣漪，或把游標以外的區域壓暗
（聚光燈）。教學、簡報與錄影時讓觀眾看得見滑鼠在哪。點擊穿透，不影響操作。

Cursor emphasis: a ring around the pointer, a ripple when you click, or a
spotlight that dims everything except a circle around the cursor — so an
audience can follow the mouse during a demo. Click-through throughout.
"""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QPoint, QTimer, Qt
from PySide6.QtGui import QColor, QCursor, QPainter, QRadialGradient

from frontengine.show.base_widget import BaseWidget
from frontengine.utils.logging.loggin_instance import front_engine_logger

DEFAULT_RING_COLOR = "#ffcc00"
DEFAULT_RING_RADIUS = 28
DEFAULT_SPOTLIGHT_RADIUS = 160
RIPPLE_STEPS = 12
_MIN_RADIUS = 8
_MAX_RADIUS = 600


def clamp_radius(value, fallback: int = DEFAULT_RING_RADIUS) -> int:
    """把半徑夾在看得見又不至於蓋滿螢幕的範圍。"""
    try:
        return max(_MIN_RADIUS, min(_MAX_RADIUS, int(value)))
    except (TypeError, ValueError):
        return fallback


def ripple_radius(step: int, base_radius: int, steps: int = RIPPLE_STEPS) -> int:
    """漣漪第 step 幀的半徑：從基準半徑往外擴散一倍。"""
    total = max(1, int(steps))
    progress = min(max(int(step), 0), total) / total
    return int(clamp_radius(base_radius) * (1.0 + progress))


def ripple_alpha(step: int, steps: int = RIPPLE_STEPS) -> int:
    """漣漪第 step 幀的透明度：越擴散越淡，最後消失。"""
    total = max(1, int(steps))
    progress = min(max(int(step), 0), total) / total
    return max(0, int(200 * (1.0 - progress)))


class CursorEffectWidget(BaseWidget):
    """
    游標效果層：亮環、點擊漣漪、聚光燈可各自開關，全部跟著游標移動。
    位置與點擊事件由外部注入（正式路徑接系統游標與全域滑鼠監聽），方便測試。
    """

    REFRESH_MS = 16

    def __init__(self, ring: bool = True, ripple: bool = True, spotlight: bool = False,
                 color: str = DEFAULT_RING_COLOR, radius: int = DEFAULT_RING_RADIUS,
                 spotlight_radius: int = DEFAULT_SPOTLIGHT_RADIUS, dim: int = 55) -> None:
        front_engine_logger.info(
            f"[CursorEffectWidget] Init | ring={ring}, ripple={ripple}, spotlight={spotlight}")
        super().__init__()
        self.opacity = 1.0
        self.show_ring = bool(ring)
        self.show_ripple = bool(ripple)
        self.show_spotlight = bool(spotlight)
        self.color = QColor(color) if QColor(color).isValid() else QColor(DEFAULT_RING_COLOR)
        self.radius = clamp_radius(radius)
        self.spotlight_radius = clamp_radius(spotlight_radius, DEFAULT_SPOTLIGHT_RADIUS)
        self.dim = max(0, min(90, int(dim)))
        self.cursor_point = QPoint(0, 0)
        self.ripples: List[dict] = []
        self._cursor_provider = QCursor.pos
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.tick)

    def set_cursor_provider(self, provider) -> None:
        """注入游標位置來源（測試用）。"""
        self._cursor_provider = provider

    def set_effects(self, ring: Optional[bool] = None, ripple: Optional[bool] = None,
                    spotlight: Optional[bool] = None) -> None:
        """開關個別效果。"""
        if ring is not None:
            self.show_ring = bool(ring)
        if ripple is not None:
            self.show_ripple = bool(ripple)
        if spotlight is not None:
            self.show_spotlight = bool(spotlight)
        self.update()

    def set_style(self, color: Optional[str] = None, radius: Optional[int] = None,
                  spotlight_radius: Optional[int] = None, dim: Optional[int] = None) -> None:
        """調整顏色、半徑與壓暗程度。"""
        if color is not None:
            candidate = QColor(color)
            if candidate.isValid():
                self.color = candidate
        if radius is not None:
            self.radius = clamp_radius(radius)
        if spotlight_radius is not None:
            self.spotlight_radius = clamp_radius(spotlight_radius, DEFAULT_SPOTLIGHT_RADIUS)
        if dim is not None:
            self.dim = max(0, min(90, int(dim)))
        self.update()

    def start_following(self, interval_ms: int = REFRESH_MS) -> None:
        """開始跟隨游標。"""
        self.tick()
        self._timer.start(max(8, int(interval_ms)))

    def add_ripple(self, point: Optional[QPoint] = None) -> None:
        """在指定位置（預設為目前游標）加一圈點擊漣漪。"""
        self.ripples.append({"point": QPoint(point or self.cursor_point), "step": 0})
        self.update()

    def tick(self) -> None:
        """更新游標位置並推進漣漪動畫。"""
        try:
            position = self._cursor_provider()
        except Exception:  # pragma: no cover - defensive around injected providers
            return
        self.cursor_point = QPoint(int(position.x()) - self.x(), int(position.y()) - self.y())
        for ripple in list(self.ripples):
            ripple["step"] += 1
            if ripple["step"] > RIPPLE_STEPS:
                self.ripples.remove(ripple)
        self.update()

    def draw_content(self, painter: QPainter) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.show_spotlight:
            self._draw_spotlight(painter)
        if self.show_ring:
            ring_color = QColor(self.color)
            ring_color.setAlpha(120)
            painter.setBrush(ring_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(self.cursor_point, self.radius, self.radius)
        if self.show_ripple:
            for ripple in self.ripples:
                color = QColor(self.color)
                color.setAlpha(ripple_alpha(ripple["step"]))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(color)
                radius = ripple_radius(ripple["step"], self.radius)
                painter.drawEllipse(ripple["point"], radius, radius)

    def _draw_spotlight(self, painter: QPainter) -> None:
        """把游標以外壓暗，中心保持透明，邊緣柔和過渡。"""
        shade = QColor(0, 0, 0, int(255 * self.dim / 100.0))
        gradient = QRadialGradient(self.cursor_point, self.spotlight_radius)
        gradient.setColorAt(0.0, QColor(0, 0, 0, 0))
        gradient.setColorAt(0.75, QColor(0, 0, 0, 0))
        gradient.setColorAt(1.0, shade)
        painter.fillRect(self.rect(), shade)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(self.cursor_point, self.spotlight_radius, self.spotlight_radius)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

    def closeEvent(self, event) -> None:
        if self._timer.isActive():
            self._timer.stop()
        super().closeEvent(event)
