"""Three-ink drawing primitives shared by every INKSIDE part.

A part is described once with a :class:`Brush`; the builder replays that
description once per output layer. Each call only paints when the brush is
rendering the layer it names, so fills, fixed paper details and the ink layer
stay separate PNGs and palette tints never touch outlines.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPainterPathStroker, QPen, QPolygonF

INK = '#1C1A17'
ORANGE = '#F2602A'
PAPER = '#F3EBDC'
STROKE = 6.0
FIXED = ('paper', 'ink')


def polygon(*points) -> QPainterPath:
    path = QPainterPath()
    path.addPolygon(QPolygonF([QPointF(x, y) for x, y in points]))
    path.closeSubpath()
    return path


def ellipse(cx: float, cy: float, rx: float, ry: float) -> QPainterPath:
    path = QPainterPath()
    path.addEllipse(QPointF(cx, cy), rx, ry)
    return path


def rounded(x: float, y: float, w: float, h: float, r: float) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(QRectF(x, y, w, h), r, r)
    return path


def rect(x: float, y: float, w: float, h: float) -> QPainterPath:
    path = QPainterPath()
    path.addRect(QRectF(x, y, w, h))
    return path


def line(*points) -> QPainterPath:
    path = QPainterPath(QPointF(*points[0]))
    for point in points[1:]:
        path.lineTo(QPointF(*point))
    return path


def stroked(path: QPainterPath, width: float) -> QPainterPath:
    """A thick round-capped stroke as a fillable shape (tails, antennas, legs)."""
    stroker = QPainterPathStroker()
    stroker.setWidth(width)
    stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
    stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return stroker.createStroke(path).simplified()


class Brush:
    """Paint only the requested layer; ``probe`` mode records the layers used."""

    def __init__(self, painter: QPainter | None, layer: str | None, colors: dict[str, str]) -> None:
        self.painter = painter
        self.layer = layer
        self.colors = colors
        self.used: list[str] = []

    def _wants(self, layer: str) -> bool:
        if layer not in self.used:
            self.used.append(layer)
        return self.painter is not None and layer == self.layer

    def fill(self, path: QPainterPath, region: str) -> None:
        """Fill a palette region, the fixed paper layer, or solid ink."""
        if self._wants(region):
            color = INK if region == 'ink' else PAPER if region == 'paper' else self.colors[region]
            self.painter.fillPath(path, QColor(color))

    def solid(self, path: QPainterPath) -> None:
        self.fill(path, 'ink')

    def outline(self, path: QPainterPath, width: float = STROKE) -> None:
        if self._wants('ink'):
            pen = QPen(QColor(INK), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                       Qt.PenJoinStyle.RoundJoin)
            self.painter.strokePath(path, pen)

    def rim(self, path: QPainterPath, width: float = 4.0, base: float = STROKE) -> None:
        """A paper knockout around an ink shape so black never merges into black."""
        if self._wants('paper'):
            pen = QPen(QColor(PAPER), base + 2 * width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                       Qt.PenJoinStyle.RoundJoin)
            self.painter.strokePath(path, pen)

    def mark(self, path: QPainterPath, width: float) -> None:
        """An ink stroke that stays legible on dark regions thanks to a thin rim."""
        self.rim(path, 2.0, width)
        self.outline(path, width)

    def shape(self, path: QPainterPath, region: str, width: float = STROKE) -> None:
        """The common case: a flat region bounded by an ink contour."""
        self.fill(path, region)
        self.outline(path, width)

    def clip(self, path: QPainterPath, draw) -> None:
        """Run ``draw`` with painting restricted to ``path``."""
        if self.painter is None:
            draw()
            return
        self.painter.save()
        self.painter.setClipPath(path, Qt.ClipOperation.IntersectClip)
        draw()
        self.painter.restore()
