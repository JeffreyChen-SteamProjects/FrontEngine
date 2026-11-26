"""
螢幕塗鴉層：在畫面上用筆或螢光筆畫線、清除、復原。畫圖時需要接收滑鼠，
所以它不是點擊穿透的；關閉塗鴉即恢復原本的操作。

A screen annotation layer: draw over the screen with a pen or highlighter,
undo, and clear. It has to take the mouse while you draw, so unlike the other
overlays it is not click-through — turn it off and the screen is yours again.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QImage, QKeySequence, QPainter, QPainterPath, QPen

from frontengine.show.base_widget import BaseWidget
from frontengine.show.presentation.annotation_toolbar import AnnotationToolbar
from frontengine.show.window_helpers import CATCH_MOUSE_COLOR, apply_overlay_window_flags
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


def stroke_path(points: List[QPoint]) -> QPainterPath:
    """One path through the points: drawn as a single stroke, a highlighter stays evenly
    translucent instead of darkening where two segments overlap."""
    path = QPainterPath(points[0])
    for point in points[1:]:
        path.lineTo(point)
    return path


def paint_stroke(painter: QPainter, stroke: dict) -> None:
    """Paint one recorded stroke; the eraser paints the catch colour back rather than clearing."""
    points = stroke["points"]
    if len(points) < 2:
        return
    color, width = stroke_style(stroke["tool"], stroke["color"], stroke["width"])
    mode = QPainter.CompositionMode.CompositionMode_SourceOver
    if stroke["tool"] == TOOL_ERASER:
        color, mode = CATCH_MOUSE_COLOR, QPainter.CompositionMode.CompositionMode_Source
    painter.setCompositionMode(mode)
    painter.setPen(QPen(color, width, Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(stroke_path(points))
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)


class AnnotationOverlay(BaseWidget):
    """
    塗鴉層：滑鼠拖曳畫線，支援筆／螢光筆／橡皮擦、復原與全部清除。
    每一筆記成 (工具, 顏色, 線寬, 點清單)，因此復原與重繪都很單純。
    """

    # A full-monitor see-through layer: on the GPU compositor the transparency could come out
    # black on some drivers (see BaseWidget).
    software_only = True
    # Drawing over a full-screen slide show is what this layer is for.
    stays_while_paused = True

    # The on-screen toolbar changed a setting (tool, colour): the page follows.
    tool_changed = Signal(str)
    color_changed = Signal(str)
    # Esc or the toolbar's button: the layer covers the settings window, so it offers its own way out.
    finish_requested = Signal()

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
        # Finished strokes, painted once; only the stroke under the pen is drawn live.
        self._finished: Optional[QImage] = None
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.toolbar = AnnotationToolbar(self)

    def set_annotation_window_flag(self) -> None:
        """塗鴉需要接收滑鼠，所以不使用點擊穿透。"""
        apply_overlay_window_flags(self, show_on_bottom=False, allow_input=True)

    def set_tool(self, tool: str) -> None:
        if tool in TOOLS:
            self.tool = tool
            self.toolbar.refresh()

    def choose_tool(self, tool: str) -> None:
        """A tool picked on the toolbar."""
        self.set_tool(tool)
        self.tool_changed.emit(self.tool)

    def choose_color(self, color: str) -> None:
        """A colour picked on the toolbar; an eraser in hand becomes a pen again."""
        self.set_pen(color=color)
        self.color_changed.emit(color)
        if self.tool == TOOL_ERASER:
            self.choose_tool(TOOL_PEN)

    def set_pen(self, color: Optional[str] = None, width: Optional[int] = None) -> None:
        if color is not None:
            self.pen_color = color
        if width is not None:
            self.pen_width = clamp_width(width)
        self.toolbar.refresh()

    def clear(self) -> None:
        """清掉所有筆畫 / Wipe every stroke."""
        self.strokes = []
        self._current = None
        self._finished = None
        self.update()

    def undo(self) -> bool:
        """收回最後一筆；沒有筆畫可收時回傳 False。"""
        if not self.strokes:
            return False
        self.strokes.pop()
        self._current = None
        self._finished = None
        self.update()
        return True

    # --- drawing ---------------------------------------------------------
    def begin_stroke(self, point: QPoint) -> None:
        self._current = {
            "tool": self.tool, "color": self.pen_color, "width": self.pen_width, "points": [point],
        }
        self.strokes.append(self._current)

    def extend_stroke(self, point: QPoint) -> None:
        if self._current is None:
            return
        points = self._current["points"]
        points.append(point)
        _color, width = stroke_style(self._current["tool"], self._current["color"], self._current["width"])
        margin = width // 2 + 3
        # The last two segments: their join is redrawn when a new one is added.
        region = QRect(points[-1], points[-1])
        for earlier in points[-3:-1]:
            region = region.united(QRect(earlier, earlier))
        self.update(region.adjusted(-margin, -margin, margin, margin))

    def end_stroke(self) -> None:
        # 只有一個點的筆畫畫不出線，直接丟掉
        # A single-point stroke draws nothing; drop it.
        if self._current is not None:
            if len(self._current["points"]) < 2:
                self.strokes.remove(self._current)
                self.update()
            elif self._finished is not None:
                painter = QPainter(self._finished)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                paint_stroke(painter, self._current)
                painter.end()
        self._current = None

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.begin_stroke(event.position().toPoint())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        self.extend_stroke(event.position().toPoint())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        # Another button let go while the left one still draws must not cut the stroke short.
        if event.button() == Qt.MouseButton.LeftButton:
            self.end_stroke()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.finish_requested.emit()
        elif event.matches(QKeySequence.StandardKey.Undo):
            self.undo()
        else:
            super().keyPressEvent(event)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.activateWindow()            # so Esc and Ctrl+Z reach this layer, not the program below
        self.setFocus(Qt.FocusReason.OtherFocusReason)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._finished = None
        self.toolbar.place()

    def _finished_strokes(self) -> QImage:
        """Every finished stroke over the catch colour, rebuilt after undo, clear, resize or a DPI change."""
        ratio = self.devicePixelRatioF()
        width, height = max(1, round(self.width() * ratio)), max(1, round(self.height() * ratio))
        cached = self._finished
        if cached is not None and (cached.width(), cached.height()) == (width, height):
            return cached
        image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        image.setDevicePixelRatio(ratio)
        image.fill(CATCH_MOUSE_COLOR)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for stroke in self.strokes:
            if stroke is not self._current:
                paint_stroke(painter, stroke)
        painter.end()
        self._finished = image
        return image

    def draw_content(self, painter: QPainter) -> None:
        # Full opacity for the whole layer: scaled by a lower opacity, the 1/255 catch alpha
        # would round to 0 and the clicks would fall through again.
        painter.setOpacity(1.0)
        painter.drawImage(QPoint(0, 0), self._finished_strokes())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._current is not None:
            paint_stroke(painter, self._current)
