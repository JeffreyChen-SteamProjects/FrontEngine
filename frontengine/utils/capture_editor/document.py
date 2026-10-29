"""Non-destructive edits in original physical-image coordinates."""
from __future__ import annotations

from copy import deepcopy
import math

from PySide6.QtCore import QPointF, QRect, QRectF, Qt, QSaveFile, QIODevice
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPolygonF, QFont


class CaptureDocument:
    """Retain one original, bounded vector marks and a twenty-step undo stack."""

    def __init__(self, image: QImage) -> None:
        if image.isNull() or image.width() * image.height() > 16_777_216:
            raise ValueError('Capture must be a valid image within 16 megapixels')
        self.original = image.copy()
        self.original.setDevicePixelRatio(1)
        self.crop = self.original.rect()
        self.marks = []
        self.history = []

    def _checkpoint(self) -> None:
        self.history.append((QRect(self.crop), deepcopy(self.marks)))
        del self.history[:-20]

    def add(self, kind: str, start: tuple[float, float], end: tuple[float, float], text: str = '') -> None:
        """Add a bounded arrow, numbered badge, text box or opaque redaction."""
        if kind not in ('arrow', 'number', 'text', 'redact') or len(self.marks) >= 1000:
            raise ValueError('Choose a supported mark; at most 1000 marks')
        if not isinstance(text, str) or len(text) > 2000:
            raise ValueError('Text must be within 2000 characters')
        points = [self._point(point) for point in (start, end)]
        if kind == 'number':
            text = str(1 + sum(mark['kind'] == 'number' for mark in self.marks))
        self._checkpoint()
        self.marks.append(dict(kind=kind, start=points[0], end=points[1], text=text))

    def _point(self, point) -> tuple[float, float]:
        if len(point) != 2 or not all(isinstance(value, (int, float)) and math.isfinite(value) for value in point):
            raise ValueError('Coordinates must be finite pairs')
        return (max(0, min(self.original.width(), point[0])), max(0, min(self.original.height(), point[1])))

    def set_crop(self, start: tuple[float, float], end: tuple[float, float]) -> None:
        """Intersect crop with the existing visible region; edits retain original coordinates."""
        rect = QRectF(QPointF(*self._point(start)), QPointF(*self._point(end))).normalized().toAlignedRect()
        rect = rect.intersected(self.crop)
        if rect.width() < 2 or rect.height() < 2:
            raise ValueError('Crop must contain at least 2×2 pixels')
        self._checkpoint()
        self.crop = rect

    def undo(self) -> bool:
        """Restore the previous crop/marks without copying the original image."""
        if not self.history:
            return False
        self.crop, self.marks = self.history.pop()
        return True

    def reset(self) -> None:
        """Restore the original visible area and remove all marks, with undo available."""
        self._checkpoint()
        self.crop, self.marks = self.original.rect(), []

    def render(self) -> QImage:
        """Flatten the current crop and marks; redactions are solid and drawn last."""
        image = self.original.copy(self.crop).convertToFormat(QImage.Format.Format_ARGB32)
        painter = QPainter(image)
        painter.translate(-self.crop.x(), -self.crop.y())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for mark in self.marks:
            if mark['kind'] != 'redact':
                self._paint(painter, mark)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        for mark in self.marks:
            if mark['kind'] == 'redact':
                painter.fillRect(QRectF(QPointF(*mark['start']), QPointF(*mark['end'])).normalized().toAlignedRect(), Qt.GlobalColor.black)
        painter.end()
        return image

    def save(self, path: str) -> bool:
        """Atomically save only flattened PNG pixels and preserve a file on failure."""
        target = QSaveFile(path)
        if not target.open(QIODevice.OpenModeFlag.WriteOnly):
            return False
        if not self.render().save(target, 'PNG'):
            target.cancelWriting()
            return False
        return target.commit()

    @staticmethod
    def _paint(painter: QPainter, mark: dict) -> None:
        start, end = QPointF(*mark['start']), QPointF(*mark['end'])
        painter.setPen(QPen(QColor('#ff3030'), 3))
        painter.setBrush(QColor('#ff3030'))
        painter.setFont(QFont('Sans Serif', 16, QFont.Weight.Bold))
        if mark['kind'] == 'arrow':
            painter.drawLine(start, end)
            angle = math.atan2(end.y() - start.y(), end.x() - start.x())
            wings = [QPointF(end.x()-14*math.cos(angle+d), end.y()-14*math.sin(angle+d)) for d in (-.5, .5)]
            painter.drawPolygon(QPolygonF([end, *wings]))
        elif mark['kind'] == 'number':
            rect = QRectF(start.x()-16, start.y()-16, 32, 32)
            painter.drawEllipse(rect)
            painter.setPen(Qt.GlobalColor.white)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, mark['text'])
        else:
            rect = QRectF(start, end).normalized()
            if rect.width() < 32 or rect.height() < 24:
                rect = QRectF(start.x(), start.y(), 240, 80)
            painter.setBrush(QColor(255, 255, 255, 230))
            painter.drawRect(rect)
            painter.drawText(rect.adjusted(5, 3, -5, -3), Qt.TextFlag.TextWordWrap, mark['text'])
