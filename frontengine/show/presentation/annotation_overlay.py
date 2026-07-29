"""
螢幕塗鴉層：在畫面上用筆或螢光筆畫線、清除、復原。畫圖時需要接收滑鼠，
所以它不是點擊穿透的；關閉塗鴉即恢復原本的操作。

A screen annotation layer: draw over the screen with a pen or highlighter,
undo, and clear. It has to take the mouse while you draw, so unlike the other
overlays it is not click-through — turn it off and the screen is yours again.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QPainter, QPen

from frontengine.show.base_widget import BaseWidget
from frontengine.show.window_helpers import apply_overlay_window_flags
from frontengine.utils.logging.loggin_instance import front_engine_logger

TOOL_PEN = "pen"
TOOL_HIGHLIGHTER = "highlighter"
TOOL_ERASER = "eraser"
TOOLS = (TOOL_PEN, TOOL_HIGHLIGHTER, TOOL_ERASER)

PEN_COLORS = (
    ("Red", "#ff3b30"), ("Yellow", "#ffcc00"), ("Green", "#34c759"),
    ("Blue", "#0a84ff"), ("Black", "#000000"), ("White", "#ffffff"),
)
DEFAULT_PEN_COLOR = "#ff3b30"
MIN_WIDTH = 1
MAX_WIDTH = 40


def clamp_width(value, fallback: int = 4) -> int:
    """把筆寬夾在可用範圍。"""
    try:
        return max(MIN_WIDTH, min(MAX_WIDTH, int(value)))
    except (TypeError, ValueError):
        return fallback


def stroke_style(tool: str, color: str, width: int) -> Tuple[QColor, int]:
    """
    依工具決定實際的顏色與線寬：螢光筆是半透明的粗線，橡皮擦畫得更粗。
    Per-tool colour and width: a highlighter is a wide translucent stroke, an
    eraser is wider still.
    """
    pen_color = QColor(color)
    if not pen_color.isValid():
        pen_color = QColor(DEFAULT_PEN_COLOR)
    stroke_width = clamp_width(width)
    if tool == TOOL_HIGHLIGHTER:
        pen_color.setAlpha(90)
        stroke_width = clamp_width(stroke_width * 4)
    elif tool == TOOL_ERASER:
        stroke_width = clamp_width(stroke_width * 5)
    return (pen_color, stroke_width)


class AnnotationOverlay(BaseWidget):
    """
    塗鴉層：滑鼠拖曳畫線，支援筆／螢光筆／橡皮擦、復原與全部清除。
    每一筆記成 (工具, 顏色, 線寬, 點清單)，因此復原與重繪都很單純。
    """

    def __init__(self, color: str = DEFAULT_PEN_COLOR, width: int = 4, tool: str = TOOL_PEN) -> None:
        front_engine_logger.info(f"[AnnotationOverlay] Init | tool={tool}, color={color}, width={width}")
        super().__init__()
        self.opacity = 1.0
        # 這一層的滑鼠是拿來畫畫的：不能被基底拖走，也不能被「鎖定覆蓋層」
        # 變成點擊穿透——那會讓畫筆整個失效，而畫好的線還留在畫面上。
        # The mouse here is the pen: the base class must not drag the window with
        # it, and "lock overlays" must not make it click-through - that kills the
        # pen outright while the strokes stay frozen on screen.
        self.overlay_lockable = False
        self.overlay_draggable = False
        self.overlay_remembers_geometry = False
        self.tool = tool if tool in TOOLS else TOOL_PEN
        self.pen_color = color
        self.pen_width = clamp_width(width)
        self.strokes: List[dict] = []
        self._current: Optional[dict] = None
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_annotation_window_flag(self) -> None:
        """塗鴉需要接收滑鼠，所以不使用點擊穿透。"""
        apply_overlay_window_flags(self, show_on_bottom=False, allow_input=True)

    def set_tool(self, tool: str) -> None:
        if tool in TOOLS:
            self.tool = tool

    def set_pen(self, color: Optional[str] = None, width: Optional[int] = None) -> None:
        if color is not None:
            self.pen_color = color
        if width is not None:
            self.pen_width = clamp_width(width)

    def clear(self) -> None:
        """清掉所有筆畫 / Wipe every stroke."""
        self.strokes = []
        self._current = None
        self.update()

    def undo(self) -> bool:
        """收回最後一筆；沒有筆畫可收時回傳 False。"""
        if not self.strokes:
            return False
        self.strokes.pop()
        self.update()
        return True

    # --- drawing ---------------------------------------------------------
    def begin_stroke(self, point: QPoint) -> None:
        self._current = {
            "tool": self.tool, "color": self.pen_color, "width": self.pen_width, "points": [point],
        }
        self.strokes.append(self._current)

    def extend_stroke(self, point: QPoint) -> None:
        if self._current is not None:
            self._current["points"].append(point)
            self.update()

    def end_stroke(self) -> None:
        # 只有一個點的筆畫畫不出線，直接丟掉
        # A single-point stroke draws nothing; drop it.
        if self._current is not None and len(self._current["points"]) < 2:
            self.strokes.remove(self._current)
            self.update()
        self._current = None

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.begin_stroke(event.position().toPoint())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        self.extend_stroke(event.position().toPoint())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self.end_stroke()
        super().mouseReleaseEvent(event)

    def draw_content(self, painter: QPainter) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for stroke in self.strokes:
            points = stroke["points"]
            if len(points) < 2:
                continue
            color, width = stroke_style(stroke["tool"], stroke["color"], stroke["width"])
            if stroke["tool"] == TOOL_ERASER:
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            else:
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setPen(QPen(color, width, Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            for start, end in zip(points, points[1:]):
                painter.drawLine(start, end)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
