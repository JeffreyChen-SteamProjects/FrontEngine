"""One active movement target for native Puppet calls and light play."""
from math import hypot
from time import monotonic

from PySide6.QtCore import QObject, QTimer

from frontengine.show.pet.target_marker import TargetMarker
from frontengine.show.pet.ball_toy import BallToy


class PuppetTargetController(QObject):
    activities = {'call': ('call', 'greet'), 'light': ('light', 'play'), 'ball': ('ball', None)}
    behaviour = 'wander'

    def __init__(self, pet):
        super().__init__(pet)
        self.pet = pet
        self.marker = None
        self._guidance = None
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.tick)

    def _geometry(self):
        screen = self.pet.screen()
        if screen is None:
            return None
        area = screen.availableGeometry()
        if max(32, self.pet.width()) > area.width() or max(32, self.pet.height()) > area.height():
            return None
        return area.x(), area.y(), area.width(), area.height(), self.pet.width(), self.pet.height()

    def _limits(self):
        return self._center_limits(16)

    def _center_limits(self, margin=0):
        left, top, width, height, pet_width, pet_height = self._geometry_signature
        cx, cy = (pet_width - 1) // 2, (pet_height - 1) // 2
        return (left + max(margin, cx), top + max(margin, cy),
                left + width - max(margin, pet_width - cx),
                top + height - max(margin, pet_height - cy))

    @property
    def bounds(self):
        left, top, width, height, _, _ = self._geometry_signature
        return left, top, left + width, top + height

    def set_guidance(self, x, y):
        self._guidance = (x, y)

    def clear_guidance(self):
        self._guidance = None

    def start(self, *, activity='call', offset=None):
        appearance, arrival_action = self.activities[activity]
        geometry = self._geometry()
        if not self.pet.can_play_with_toy or geometry is None:
            return 'busy'
        self.stop()
        self._geometry_signature = geometry
        self._mode_revision = self.pet.profile_session.mode_revision
        self._x, self._y = float(self.pet.x()), float(self.pet.y())
        self._elapsed = 0.0
        self._last_time = monotonic()
        self.arrival_action = arrival_action
        self.marker = (BallToy(self.pet, motion=self, return_tolerance=2) if activity == 'ball'
                       else TargetMarker(self.pet, limits=self._limits, offset=offset, appearance=appearance))
        self.pet.placement_revision += 1
        self.marker.show()
        self.timer.start()
        self.pet.set_settled(self.pet._settled)
        return 'accepted'

    def validate(self):
        if self.marker is not None and (
                not self.pet.can_play_with_toy
                or self.pet.profile_session.mode_revision != self._mode_revision
                or self._geometry() != self._geometry_signature):
            self.stop()

    def tick(self, elapsed=None):
        self.validate()
        marker = self.marker
        if marker is None:
            return
        now = monotonic()
        dt = max(0, min(0.05, now - self._last_time if elapsed is None else elapsed))
        self._last_time = now
        if isinstance(marker, BallToy):
            marker.tick(dt)
            if self.marker is marker and not marker.dragging and self._guidance is not None:
                self._move_towards(self._guidance, dt)
            return
        self._elapsed += dt
        if self._elapsed >= 30:
            self.stop()
            return
        self._move_towards(marker.target, dt)
        actual_x, actual_y = self.pet.center()
        nearby = hypot(marker.target[0] - actual_x, marker.target[1] - actual_y) <= 2
        marker._near_time = marker._near_time + dt if nearby and not marker.dragging else 0.0
        if marker._near_time >= 0.5:
            arrival_action = self.arrival_action
            self.stop()
            self.pet._interaction_feedback(self.pet.profile_session.request(arrival_action))

    def _move_towards(self, target, dt):
        left, top, right, bottom = self._center_limits()
        target_x, target_y = max(left, min(target[0], right)), max(top, min(target[1], bottom))
        cx, cy = (self.pet.width() - 1) // 2, (self.pet.height() - 1) // 2
        dx, dy = target_x - cx - self._x, target_y - cy - self._y
        distance = hypot(dx, dy)
        if distance:
            step = min(distance, 160 * dt)
            self._x += dx * step / distance
            self._y += dy * step / distance
            self.pet.move(round(self._x), round(self._y))

    def stop(self):
        marker, self.marker = self.marker, None
        self.timer.stop()
        self.clear_guidance()
        if marker is not None:
            marker.close()
            marker.deleteLater()
            if not self.pet._closed:
                self.pet.set_settled(self.pet._settled)
