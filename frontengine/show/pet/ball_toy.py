"""A pet-owned throwable ball, bounded to its current activity area."""
from time import monotonic

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget
from frontengine.utils.multi_language.retranslate import tr


class BallToy(QWidget):
    def __init__(self, pet, *, motion=None, return_tolerance=None):
        super().__init__(pet, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(28, 28)
        self.pet = pet
        self.motion = motion if motion is not None else pet.motion
        self.return_tolerance = return_tolerance
        tr(self, 'pet_ball_start', 'Throw a ball', 'setAccessibleName')
        tr(self, 'pet_ball_hint', 'Drag and release to throw again. Right-click to put the ball away.', 'setToolTip')
        self.phase = 'flight'
        self.origin = pet.center()
        self.xpos, self.ypos = map(float, self.origin)
        left, top, right, bottom = self.motion.bounds
        self.vx = 180.0 if self.xpos < (left + right) / 2 else -180.0
        self.vy = -220.0
        self.dragging = False
        self._last_pointer = None
        self._last_time = monotonic()
        self._elapsed = 0.0
        self._clamp()
        self.move(round(self.xpos), round(self.ypos))

    def _clamp(self):
        left, top, right, bottom = self.motion.bounds
        self.xpos = max(left, min(self.xpos, right - self.width()))
        self.ypos = max(top, min(self.ypos, bottom - self.height()))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor('#171717'), 3))
        painter.setBrush(QColor('#f37620'))
        painter.drawEllipse(2, 2, 24, 24)
        painter.setPen(QPen(QColor('#fff4dc'), 3))
        painter.drawArc(7, 5, 14, 18, -70 * 16, 140 * 16)
        painter.end()

    def tick(self, elapsed=None):
        now = monotonic()
        dt = max(0, min(0.05, now - self._last_time if elapsed is None else elapsed))
        self._last_time = now
        self._elapsed += dt
        if self._elapsed > 30:
            self.pet.stop_toy()
            return
        if self.dragging:
            return
        left, top, right, bottom = self.motion.bounds
        if self.phase == 'flight':
            self.vy += 650 * dt
            self.xpos += self.vx * dt
            self.ypos += self.vy * dt
            if self.xpos <= left or self.xpos + self.width() >= right:
                self.vx *= -0.6
            if self.ypos <= top:
                self.vy = abs(self.vy)
            if self.ypos + self.height() >= bottom:
                self.vy = -abs(self.vy) * 0.45
                self.vx *= 0.7
                if abs(self.vy) < 25:
                    self.vy = 0
                    self.phase = 'chase'
            self._clamp()
        center = (self.xpos + 14, self.ypos + 14)
        if self.phase in ('flight', 'chase'):
            self.motion.set_guidance(*center)
            if self.phase == 'chase' and self.pet.geometry().adjusted(-10, -10, 10, 10).contains(*map(round, center)):
                self.phase = 'return'
        if self.phase == 'return':
            self.motion.set_guidance(*self.origin)
            px, py = self.pet.center()
            self.xpos, self.ypos = px - 14, py - 14
            self._clamp()
            tolerance = self.return_tolerance if self.return_tolerance is not None else max(12, self.motion.speed * 2)
            horizontal = abs(px - self.origin[0]) <= tolerance
            vertical = self.motion.behaviour == 'floor' or abs(py - self.origin[1]) <= tolerance
            if horizontal and vertical:
                self.pet.profile_session.reward('ball')
                self.pet.stop_toy()
                return
        self.move(round(self.xpos), round(self.ypos))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.pet.stop_toy()
        elif event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.motion.clear_guidance()
            self._last_pointer = (event.globalPosition(), monotonic())
            self.vx = self.vy = 0
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging:
            point, now = event.globalPosition(), monotonic()
            previous, before = self._last_pointer
            seconds = max(0.01, now - before)
            self.vx = max(-600, min(600, (point.x() - previous.x()) / seconds))
            self.vy = max(-600, min(600, (point.y() - previous.y()) / seconds))
            self._last_pointer = (point, now)
            self.xpos, self.ypos = point.x() - 14, point.y() - 14
            self._clamp()
            self.move(round(self.xpos), round(self.ypos))
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.dragging:
            self.dragging = False
            self.phase = 'flight'
            self._elapsed = 0
            self._last_time = monotonic()
            event.accept()
