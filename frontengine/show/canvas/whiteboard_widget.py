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
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen

from frontengine.show.base_widget import BaseWidget
from frontengine.show.window_helpers import apply_overlay_window_flags
from frontengine.utils.logging.loggin_instance import front_engine_logger

DEFAULT_COLOR = "#ffd54f"
DEFAULT_WIDTH = 4
MIN_ZOOM = 0.2
MAX_ZOOM = 5.0
ZOOM_STEP = 1.15
_SAVE_MARGIN = 24


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
        self.pen_width = max(1, int(width))
        self.opacity = 1.0
        self.overlay_lockable = False
        # 白板自己處理拖曳（畫線與平移），基底的拖曳擺位會把整塊畫布搬走
        # The whiteboard handles its own dragging - strokes and panning - and the
        # base class's drag-to-position would carry the whole canvas off with it.
        self.overlay_draggable = False
        self.overlay_remembers_geometry = False
        self.strokes: List[Dict[str, Any]] = []
        self.zoom = 1.0
        self.offset = [0.0, 0.0]
        self._stroke: Optional[Dict[str, Any]] = None
        self._pan_origin: Optional[QPoint] = None
        apply_overlay_window_flags(self, show_on_bottom=False, allow_input=True)

    # --- drawing ---------------------------------------------------------
    def begin_stroke(self, point: QPoint) -> None:
        """開始一筆。"""
        self._stroke = {"color": self.color.name(), "width": self.pen_width,
                        "points": [to_canvas((point.x(), point.y()), self.offset, self.zoom)]}

    def extend_stroke(self, point: QPoint) -> None:
        if self._stroke is not None:
            self._stroke["points"].append(to_canvas((point.x(), point.y()), self.offset, self.zoom))
            self.update()

    def end_stroke(self) -> bool:
        """
        收筆。只有一個點的「筆畫」是誤點，丟掉不留。
        Finish. A one-point stroke is a stray click and is discarded.
        """
        stroke, self._stroke = self._stroke, None
        if stroke is None or len(stroke["points"]) < 2:
            return False
        self.strokes.append(stroke)
        self.update()
        return True

    def undo(self) -> bool:
        """收回最後一筆。"""
        if not self.strokes:
            return False
        self.strokes.pop()
        self.update()
        return True

    def clear(self) -> None:
        self.strokes = []
        self._stroke = None
        self.update()

    def set_pen(self, color: Optional[str] = None, width: Optional[int] = None) -> None:
        if color is not None:
            candidate = QColor(color)
            if candidate.isValid():
                self.color = candidate
        if width is not None:
            self.pen_width = max(1, int(width))

    # --- navigating ------------------------------------------------------
    def pan(self, dx: float, dy: float) -> None:
        """平移畫布。"""
        self.offset[0] += float(dx)
        self.offset[1] += float(dy)
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
        if event.button() == Qt.MouseButton.LeftButton:
            self.begin_stroke(event.position().toPoint())
        elif event.button() == Qt.MouseButton.MiddleButton:
            self._pan_origin = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        point = event.position().toPoint()
        if self._pan_origin is not None:
            self.pan(point.x() - self._pan_origin.x(), point.y() - self._pan_origin.y())
            self._pan_origin = point
        else:
            self.extend_stroke(point)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_origin = None
        else:
            self.end_stroke()
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:
        step = ZOOM_STEP if event.angleDelta().y() > 0 else 1.0 / ZOOM_STEP
        self.zoom_at(event.position().toPoint(), step)

    # --- output ----------------------------------------------------------
    def save_image(self, path: str) -> Optional[str]:
        """
        把所有筆畫存成一張圖（只涵蓋畫過的範圍）。沒有筆畫就不存，回傳 None。
        Save the strokes as an image covering only the area drawn on. Nothing
        drawn means nothing saved.
        """
        bounds = content_bounds(self.strokes)
        if bounds is None:
            return None
        left, top, right, bottom = bounds
        width = int(right - left) + _SAVE_MARGIN * 2
        height = int(bottom - top) + _SAVE_MARGIN * 2
        image = QImage(max(1, width), max(1, height), QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        for stroke in self.strokes:
            self._paint_stroke(painter, stroke,
                               offset=(_SAVE_MARGIN - left, _SAVE_MARGIN - top), zoom=1.0)
        painter.end()
        target = Path(path)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if not image.save(str(target)):
                return None
        except OSError as error:
            front_engine_logger.warning(f"[WhiteboardWidget] save failed: {error!r}")
            return None
        front_engine_logger.info(f"[WhiteboardWidget] saved | {target}")
        return str(target)

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
        for stroke in self.strokes:
            self._paint_stroke(painter, stroke, self.offset, self.zoom)
        if self._stroke is not None:
            self._paint_stroke(painter, self._stroke, self.offset, self.zoom)
