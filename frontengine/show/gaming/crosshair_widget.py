"""
準星覆蓋層：在畫面正中央畫一個自訂準星，點擊穿透，不動到任何遊戲檔案。

這是純粹的疊圖——不注入遊戲、不讀取記憶體、不改動遊戲的任何東西。全螢幕
獨佔模式的遊戲會蓋在它上面，那是作業系統的堆疊規則，不是這裡能繞過的。

A crosshair overlay: draw a custom crosshair in the middle of the screen,
click-through, touching no game files.

It is only a layer on top - nothing is injected, no memory is read, no game is
modified. An exclusive-fullscreen game will cover it, which is how the OS
stacks windows and not something to work around.
"""
from __future__ import annotations

from typing import Any, Optional, Tuple

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QScreen

from frontengine.show.base_widget import BaseWidget
from frontengine.utils.logging.loggin_instance import front_engine_logger

STYLE_CROSS = "cross"
STYLE_DOT = "dot"
STYLE_CIRCLE = "circle"
STYLE_T_SHAPE = "t"
STYLES = (STYLE_CROSS, STYLE_DOT, STYLE_CIRCLE, STYLE_T_SHAPE)

DEFAULT_COLOR = "#00ff88"
DEFAULT_SIZE = 24
DEFAULT_THICKNESS = 2
DEFAULT_GAP = 6
MIN_SIZE = 4
MAX_SIZE = 200


def normalize_style(style: Any) -> str:
    """把準星樣式正規化；不認得的一律當十字。"""
    name = str(style or "").strip().lower()
    return name if name in STYLES else STYLE_CROSS


def clamp_size(value: Any, fallback: int = DEFAULT_SIZE) -> int:
    """準星尺寸夾在看得見又不誇張的範圍。"""
    try:
        return max(MIN_SIZE, min(MAX_SIZE, int(value)))
    except (TypeError, ValueError):
        return fallback


def clamp_thickness(value: Any, fallback: int = DEFAULT_THICKNESS) -> int:
    """線寬夾在 1~12。"""
    try:
        return max(1, min(12, int(value)))
    except (TypeError, ValueError):
        return fallback


def clamp_gap(value: Any, size: int = DEFAULT_SIZE, fallback: int = DEFAULT_GAP) -> int:
    """
    中央空隙不能大到把準星吃光，所以上限跟著尺寸走。
    The centre gap cannot swallow the crosshair, so its ceiling follows the size.
    """
    try:
        gap = int(value)
    except (TypeError, ValueError):
        gap = fallback
    return max(0, min(clamp_size(size) - 1, gap))


def arm_segments(size: int, gap: int) -> Tuple[Tuple[float, float], ...]:
    """
    十字手臂的 (起點, 終點) 距離中心多遠。因為 clamp_gap 保證空隙一定小於
    尺寸，所以手臂至少會有一個像素長——準星不會被空隙吃到看不見。
    How far each arm starts and ends from the centre. clamp_gap keeps the gap
    strictly inside the size, so an arm is always at least a pixel long: the
    crosshair can never be swallowed by its own gap.
    """
    length = clamp_size(size)
    return ((clamp_gap(gap, length), length),)


class CrosshairWidget(BaseWidget):
    """
    畫面中央的準星。位置固定在目標螢幕正中，不接受滑鼠（點擊會穿到遊戲）。
    """

    def __init__(self, style: str = STYLE_CROSS, color: str = DEFAULT_COLOR,
                 size: int = DEFAULT_SIZE, thickness: int = DEFAULT_THICKNESS,
                 gap: int = DEFAULT_GAP) -> None:
        front_engine_logger.info(f"[CrosshairWidget] Init | style={style}")
        super().__init__()
        self.style = normalize_style(style)
        candidate = QColor(color)
        self.color = candidate if candidate.isValid() else QColor(DEFAULT_COLOR)
        self.size = clamp_size(size)
        self.thickness = clamp_thickness(thickness)
        self.gap = clamp_gap(gap, self.size)
        self.opacity = 1.0
        self.resize(self.size * 2 + 8, self.size * 2 + 8)

    def set_crosshair(self, style: Optional[str] = None, color: Optional[str] = None,
                      size: Optional[int] = None,
                      thickness=None, gap=None) -> None:
        """一次改好幾項設定，改完立刻重畫。"""
        if style is not None:
            self.style = normalize_style(style)
        if color is not None:
            candidate = QColor(color)
            if candidate.isValid():
                self.color = candidate
        if size is not None:
            self.size = clamp_size(size)
        if thickness is not None:
            self.thickness = clamp_thickness(thickness)
        if gap is not None or size is not None:
            self.gap = clamp_gap(self.gap if gap is None else gap, self.size)
        self.resize(self.size * 2 + 8, self.size * 2 + 8)
        self.centre_on_screen()
        self.update()

    def centre_on_screen(self, screen: Optional[QScreen] = None) -> None:
        """擺到螢幕正中央（準星要對準的是畫面中心）。"""
        from PySide6.QtGui import QGuiApplication

        target = screen or self.screen() or QGuiApplication.primaryScreen()
        if target is None:  # pragma: no cover - no screen at all
            return
        geometry = target.geometry()
        self.move(geometry.x() + (geometry.width() - self.width()) // 2,
                  geometry.y() + (geometry.height() - self.height()) // 2)

    def draw_content(self, painter: QPainter) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(self.color, self.thickness)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen)
        centre = QPointF(self.width() / 2.0, self.height() / 2.0)
        if self.style == STYLE_DOT:
            painter.setBrush(self.color)
            painter.drawEllipse(centre, self.thickness, self.thickness)
            return
        if self.style == STYLE_CIRCLE:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(centre, float(self.size), float(self.size))
            return
        self._draw_arms(painter, centre)

    def _draw_arms(self, painter: QPainter, centre: QPointF) -> None:
        """十字與 T 字共用的手臂繪製（T 字少了上面那一隻）。"""
        for inner, outer in arm_segments(self.size, self.gap):
            painter.drawLine(QPointF(centre.x() - outer, centre.y()),
                             QPointF(centre.x() - inner, centre.y()))
            painter.drawLine(QPointF(centre.x() + inner, centre.y()),
                             QPointF(centre.x() + outer, centre.y()))
            painter.drawLine(QPointF(centre.x(), centre.y() + inner),
                             QPointF(centre.x(), centre.y() + outer))
            if self.style != STYLE_T_SHAPE:
                painter.drawLine(QPointF(centre.x(), centre.y() - outer),
                                 QPointF(centre.x(), centre.y() - inner))
