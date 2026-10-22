"""Bounded page-only image export, independent of toolbar, selection and view."""
from __future__ import annotations
import math
from PySide6.QtCore import QPointF, Qt, QSaveFile, QIODevice
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPolygonF
from frontengine.utils.whiteboard.document import normalize_document


def render_page(page: dict) -> QImage:
    """Flatten validated vector strokes without clipping wide pens or allocating huge rasters."""
    page = normalize_document({'version': 1, 'current': 0, 'pages': [page]})['pages'][0]
    strokes = page['strokes']
    if not strokes:
        raise ValueError('Draw on this page before exporting an image')
    points = [point for stroke in strokes for point in stroke['points']]
    margin = math.ceil(max(stroke['width'] for stroke in strokes) / 2) + 24
    left, top = min(point[0] for point in points), min(point[1] for point in points)
    width = math.ceil(max(point[0] for point in points)-left) + margin * 2
    height = math.ceil(max(point[1] for point in points)-top) + margin * 2
    if width > 8192 or height > 8192 or width * height > 16_777_216:
        raise ValueError('Whiteboard image exceeds 8192 pixels per side or 16 megapixels')
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    for stroke in strokes:
        pen = QPen(QColor(stroke['color']), stroke['width'])
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPolyline(QPolygonF([QPointF(x-left+margin, y-top+margin) for x,y in stroke['points']]))
    painter.end()
    return image


def save_page(page: dict, path: str, *, cancel=None) -> str:
    """Write only selected-page pixels atomically; failed or cancelled export keeps the target."""
    image = render_page(page)
    target = QSaveFile(path)
    if not target.open(QIODevice.OpenModeFlag.WriteOnly):
        raise OSError(target.errorString())
    if not image.save(target, 'PNG') or (cancel is not None and cancel.is_set()):
        target.cancelWriting()
        raise OSError('Whiteboard PNG export failed or was cancelled')
    if not target.commit():
        raise OSError(target.errorString())
    return path
