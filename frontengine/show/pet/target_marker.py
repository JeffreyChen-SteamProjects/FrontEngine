"""Nonactivating draggable target visuals, independent of pet movement."""
from math import hypot

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from frontengine.utils.multi_language.retranslate import tr


class TargetMarker(QWidget):
    def __init__(self, pet, *, limits, floor=lambda: False, offset=None, appearance='light'):
        super().__init__(pet, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(32, 32)
        self.pet, self.limits, self.floor = pet, limits, floor
        self.appearance = appearance
        self.origin = pet.center()
        self.radius = max(96, min(320, pet.width() * 2))
        self.dragging = False
        self._near_time = 0.0
        dx, dy = offset if offset is not None else (min(120, self.radius), 0)
        self.place_target(self.origin[0] + dx, self.origin[1] + dy)
        if appearance == 'call':
            tr(self, 'pet_come_hint', 'Drag the marker to a nearby destination. Right-click to cancel.', 'setToolTip')
            tr(self, 'pet_come', 'Come here', 'setAccessibleName')
        else:
            tr(self, 'pet_light_hint', 'Drag the light spot; release near the pet to play. Right-click to cancel.', 'setToolTip')
            tr(self, 'pet_light_start', 'Play with a light spot', 'setAccessibleName')

    def place_target(self, x, y):
        dx, dy = x - self.origin[0], y - self.origin[1]
        floor = self.floor()
        if floor:
            dy = 0
        distance = hypot(dx, dy)
        if distance > self.radius:
            x = self.origin[0] + dx * self.radius / distance
            y = self.origin[1] + dy * self.radius / distance
        left, top, right, bottom = self.limits()
        if floor:
            y = bottom
        self.target = (max(left, min(x, right)), max(top, min(y, bottom)))
        self.move(round(self.target[0] - 16), round(self.target[1] - 16))
        self._near_time = 0.0

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.appearance == 'call':
            painter.setPen(QPen(QColor('#171613'), 2))
            painter.setBrush(QColor('#fff1cf'))
            painter.drawEllipse(2, 2, 28, 28)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor('#ff7417'))
            painter.drawPolygon(QPolygonF([QPointF(8, 12), QPointF(24, 12), QPointF(16, 23)]))
        else:
            painter.setPen(QPen(QColor('#171717'), 2))
            painter.setBrush(QColor('#f37620'))
            painter.drawEllipse(5, 5, 22, 22)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor('#fff4dc'))
            painter.drawEllipse(12, 12, 8, 8)
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.pet.stop_toy()
        elif event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self._near_time = 0.0
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging:
            point = event.globalPosition()
            self.place_target(point.x(), point.y())
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            event.accept()
