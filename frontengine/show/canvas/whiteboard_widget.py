"""
無限畫布白板：可以一直往外畫、拖曳平移、滾輪縮放，最後存成圖片。

和簡報分頁的塗鴉層不同的是，筆畫存的是「畫布座標」而不是螢幕座標，所以平移
縮放之後線條還在它原本該在的地方——這正是「無限」的意思。

An infinite whiteboard: keep drawing outwards, drag to pan, scroll to zoom, and
save the result as an image.

Unlike the presenting page's annotation layer, strokes are stored in canvas
coordinates rather than screen ones, so panning and zooming leaves them where
they belong - which is what makes it infinite.
"""
from __future__ import annotations

from pathlib import Path
import math
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen

from frontengine.show.base_widget import BaseWidget
from frontengine.show.window_helpers import apply_overlay_window_flags
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.whiteboard.document import WhiteboardDocument, MAX_POINTS, hit_stroke
from frontengine.show.canvas.whiteboard_controls import WhiteboardControls
from frontengine.utils.whiteboard.raster import save_page
from frontengine.utils.multi_language.retranslate import translate

DEFAULT_COLOR = "#ffd54f"
DEFAULT_WIDTH = 4
MIN_ZOOM = 0.2
MAX_ZOOM = 5.0
ZOOM_STEP = 1.15


def clamp_zoom(value: Any, fallback: float = 1.0) -> float:
    """縮放倍率夾在看得清楚又不會迷路的範圍。"""
    try:
        return max(MIN_ZOOM, min(MAX_ZOOM, float(value)))
    except (TypeError, ValueError):
        return fallback


def to_canvas(point: Tuple[float, float], offset: Tuple[float, float], zoom: float) -> Tuple[float, float]:
    """螢幕座標 -> 畫布座標。"""
    scale = clamp_zoom(zoom)
    return ((point[0] - offset[0]) / scale, (point[1] - offset[1]) / scale)


def to_screen(point: Tuple[float, float], offset: Tuple[float, float], zoom: float) -> Tuple[float, float]:
    """畫布座標 -> 螢幕座標。"""
    scale = clamp_zoom(zoom)
    return (point[0] * scale + offset[0], point[1] * scale + offset[1])


def content_bounds(strokes: List[Dict[str, Any]]) -> Optional[Tuple[float, float, float, float]]:
    """
    所有筆畫涵蓋的畫布範圍 (left, top, right, bottom)；沒有筆畫回傳 None。
    存檔時用它決定要輸出多大，才不會存出一大片空白。
    The canvas area the strokes cover, or None when there are none. Saving uses
    it to size the image, so the result is not mostly blank.
    """
    points = [point for stroke in strokes for point in stroke.get("points", [])]
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return (min(xs), min(ys), max(xs), max(ys))


class WhiteboardWidget(BaseWidget):
    """
    無限畫布。筆畫以畫布座標保存，畫的時候才換算成螢幕座標。
    """

    def __init__(self, color: str = DEFAULT_COLOR, width: int = DEFAULT_WIDTH) -> None:
        front_engine_logger.info("[WhiteboardWidget] Init")
        super().__init__()
        candidate = QColor(color)
        self.color = candidate if candidate.isValid() else QColor(DEFAULT_COLOR)
        self.pen_width = max(1, min(64, int(width)))
        self.opacity = 1.0
        self.overlay_lockable = False
        # 白板自己處理拖曳（畫線與平移），基底的拖曳擺位會把整塊畫布搬走
        # The whiteboard handles its own dragging - strokes and panning - and the
        # base class's drag-to-position would carry the whole canvas off with it.
        self.overlay_draggable = False
        self.overlay_remembers_geometry = False
        self.document = WhiteboardDocument()
        self.selected = set()
        self.select_mode = False
        self._move_origin = None
        self._stroke: Optional[Dict[str, Any]] = None
        self._pan_origin: Optional[QPoint] = None
        apply_overlay_window_flags(self, show_on_bottom=False, allow_input=True)
        self.controls = WhiteboardControls(self)

    @property
    def strokes(self) -> List[Dict[str, Any]]:
        """Legacy active-page strokes access stays compatible with existing callers."""
        return self.document.page['strokes']

    @strokes.setter
    def strokes(self, value: list) -> None:
        self.document.page['strokes'] = value

    @property
    def zoom(self) -> float:
        """Return the active page's stored view scale."""
        return self.document.page['zoom']

    @zoom.setter
    def zoom(self, value: float) -> None:
        self.document.page['zoom'] = value

    @property
    def offset(self) -> list:
        """Return the active page's stored pan offset."""
        return self.document.page['offset']

    @offset.setter
    def offset(self, value: list) -> None:
        self.document.page['offset'] = value

    def select_page(self, index: int) -> None:
        """Switch independent strokes and view state; discard in-progress gestures."""
        if not 0 <= index < len(self.document.pages):
            raise ValueError('Whiteboard page is invalid')
        self.document.current = index
        self._stroke, self._move_origin, self._pan_origin = None, None, None
        self.selected.clear()
        self.controls.refresh()
        self.update()

    def add_page(self) -> None:
        """Create and display another editable page."""
        self.select_page(self.document.add_page())

    def remove_page(self) -> None:
        """Delete the active page, preserving one blank page at minimum."""
        self.document.remove_page()
        self.select_page(self.document.current)

    def load_document(self, value: dict) -> None:
        """Replace pages only after the full file passes validation."""
        self.document.replace(value)
        self.select_page(self.document.current)

    def set_select_mode(self, value: bool) -> None:
        """Choose stroke selection/movement instead of drawing new lines."""
        self.select_mode = bool(value)
        self._stroke, self._move_origin = None, None
        self.setCursor(Qt.CursorShape.ArrowCursor if value else Qt.CursorShape.CrossCursor)

    def select_at(self, point: QPoint, *, additive: bool = False) -> int | None:
        """Hit-test in canvas coordinates with a constant eight-pixel screen tolerance."""
        target = to_canvas((point.x(), point.y()), self.offset, self.zoom)
        index = hit_stroke(self.strokes, target, 8 / self.zoom)
        if index not in self.selected and not additive:
            self.selected.clear()
        if index is not None:
            if additive and index in self.selected:
                self.selected.remove(index)
            else:
                self.selected.add(index)
        self.update()
        return index

    def move_selected(self, dx: float, dy: float) -> None:
        """Move selected strokes by screen delta while respecting page bounds."""
        delta = (float(dx) / self.zoom, float(dy) / self.zoom)
        if not all(math.isfinite(value) for value in delta):
            raise ValueError('Whiteboard movement must be finite')
        points = [point for index in self.selected for point in self.strokes[index]['points']]
        if any(abs(point[axis] + delta[axis]) > 100_000 for point in points for axis in (0, 1)):
            return
        for index in self.selected:
            stroke = self.strokes[index]
            stroke['points'] = [(point[0]+delta[0], point[1]+delta[1]) for point in stroke['points']]
        self.update()

    def delete_selected(self) -> None:
        """Remove selected vector strokes from the active page only."""
        if self.selected:
            self.document.checkpoint()
            self.strokes = [stroke for index, stroke in enumerate(self.strokes) if index not in self.selected]
        self.selected.clear()
        self.update()

    # --- drawing ---------------------------------------------------------
    def begin_stroke(self, point: QPoint) -> None:
        """開始一筆。"""
        if len(self.strokes) >= 2000 or self._point_count() >= MAX_POINTS:
            self.controls._error(translate('board_limit'))
            return
        self._stroke = {"color": self.color.name(), "width": self.pen_width,
                        "points": [self._canvas_point(point)]}

    def extend_stroke(self, point: QPoint) -> None:
        if self._stroke is not None and self._point_count() + len(self._stroke['points']) < MAX_POINTS:
            self._stroke["points"].append(self._canvas_point(point))
            self.update()

    def end_stroke(self) -> bool:
        """
        收筆。只有一個點的「筆畫」是誤點，丟掉不留。
        Finish. A one-point stroke is a stray click and is discarded.
        """
        stroke, self._stroke = self._stroke, None
        if stroke is None or len(stroke["points"]) < 2:
            return False
        self.document.checkpoint()
        self.strokes.append(stroke)
        self.update()
        return True

    def _point_count(self) -> int:
        return sum(len(stroke['points']) for page in self.document.pages for stroke in page['strokes'])

    def _canvas_point(self, point: QPoint) -> tuple[float, float]:
        return tuple(max(-100_000, min(100_000, number)) for number in to_canvas((point.x(), point.y()), self.offset, self.zoom))

    def undo(self) -> bool:
        """收回最後一筆。"""
        if not self.document.undo():
            return False
        self.selected.clear()
        self.update()
        return True

    def clear(self) -> None:
        self.document.checkpoint()
        self.strokes = []
        self._stroke = None
        self.selected.clear()
        self.update()

    def set_pen(self, color: Optional[str] = None, width: Optional[int] = None) -> None:
        if color is not None:
            candidate = QColor(color)
            if candidate.isValid():
                self.color = candidate
        if width is not None:
            self.pen_width = max(1, min(64, int(width)))

    # --- navigating ------------------------------------------------------
    def pan(self, dx: float, dy: float) -> None:
        """平移畫布。"""
        self.offset[0] = max(-100_000, min(100_000, self.offset[0] + float(dx)))
        self.offset[1] = max(-100_000, min(100_000, self.offset[1] + float(dy)))
        self.update()

    def zoom_at(self, point: QPoint, factor: float) -> float:
        """
        以游標為中心縮放：游標底下的那一點在縮放前後要停在原地，
        不然放大時畫面會整個跑掉。
        Zoom around the cursor so whatever is under it stays put; otherwise the
        view lurches away every time you zoom.
        """
        before = to_canvas((point.x(), point.y()), self.offset, self.zoom)
        self.zoom = clamp_zoom(self.zoom * float(factor))
        after = to_screen(before, self.offset, self.zoom)
        self.offset[0] += point.x() - after[0]
        self.offset[1] += point.y() - after[1]
        self.update()
        return self.zoom

    def reset_view(self) -> None:
        """回到原點與原始比例（筆畫都還在）。"""
        self.zoom = 1.0
        self.offset = [0.0, 0.0]
        self.update()

    # --- events ----------------------------------------------------------
    def mousePressEvent(self, event) -> None:
        if self.controls.pending is not None:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            if self.select_mode:
                self.select_at(event.position().toPoint(), additive=bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier))
                self._move_origin = event.position().toPoint() if self.selected else None
                if self._move_origin is not None:
                    self.document.checkpoint()
            else:
                self.begin_stroke(event.position().toPoint())
        elif event.button() == Qt.MouseButton.MiddleButton:
            self._pan_origin = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        point = event.position().toPoint()
        if self._move_origin is not None:
            self.move_selected(point.x()-self._move_origin.x(), point.y()-self._move_origin.y())
            self._move_origin = point
        elif self._pan_origin is not None:
            self.pan(point.x() - self._pan_origin.x(), point.y() - self._pan_origin.y())
            self._pan_origin = point
        else:
            self.extend_stroke(point)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._move_origin = None
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_origin = None
        else:
            self.end_stroke()
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.controls.setGeometry(0, 0, self.width(), self.controls.sizeHint().height())

    def closeEvent(self, event) -> None:
        self.controls.shutdown()
        super().closeEvent(event)

    def wheelEvent(self, event) -> None:
        step = ZOOM_STEP if event.angleDelta().y() > 0 else 1.0 / ZOOM_STEP
        self.zoom_at(event.position().toPoint(), step)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and self.select_mode:
            self.delete_selected()
        elif event.key() == Qt.Key.Key_Z and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.undo()
        else:
            super().keyPressEvent(event)

    # --- output ----------------------------------------------------------
    def save_image(self, path: str) -> Optional[str]:
        """
        把所有筆畫存成一張圖（只涵蓋畫過的範圍）。沒有筆畫就不存，回傳 None。
        Save the strokes as an image covering only the area drawn on. Nothing
        drawn means nothing saved.
        """
        target = Path(path)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            return save_page(self.document.page, str(target))
        except (OSError, ValueError) as error:
            front_engine_logger.warning(f"[WhiteboardWidget] save failed: {error!r}")
            return None

    def _paint_stroke(self, painter: QPainter, stroke: Dict[str, Any],
                      offset, zoom: float) -> None:
        points = stroke.get("points", [])
        if len(points) < 2:
            return
        pen = QPen(QColor(stroke.get("color", DEFAULT_COLOR)),
                   max(1.0, float(stroke.get("width", DEFAULT_WIDTH)) * zoom))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        previous = to_screen(points[0], offset, zoom)
        for point in points[1:]:
            current = to_screen(point, offset, zoom)
            painter.drawLine(QPointF(*previous), QPointF(*current))
            previous = current

    def draw_content(self, painter: QPainter) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(QRectF(self.rect()), QColor(0, 0, 0, 120))
        for index, stroke in enumerate(self.strokes):
            self._paint_stroke(painter, stroke, self.offset, self.zoom)
            if index in self.selected:
                bounds = content_bounds([stroke])
                left, top = to_screen(bounds[:2], self.offset, self.zoom)
                right, bottom = to_screen(bounds[2:], self.offset, self.zoom)
                painter.setPen(QPen(QColor('#4dd0e1'), 1, Qt.PenStyle.DashLine))
                painter.drawRect(QRectF(left-4, top-4, right-left+8, bottom-top+8))
        if self._stroke is not None:
            self._paint_stroke(painter, self._stroke, self.offset, self.zoom)
