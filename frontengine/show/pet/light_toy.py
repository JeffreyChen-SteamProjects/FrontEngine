"""Sprite guidance and arrival on the shared draggable target marker."""
from time import monotonic

from frontengine.show.pet.target_marker import TargetMarker


class LightToy(TargetMarker):
    arrival_action = 'play'

    def __init__(self, pet, *, offset=None, appearance='light'):
        def limits():
            left, top, right, bottom = pet.motion.bounds
            return left + 16, top + 16, right - 16, bottom - 16
        super().__init__(pet, limits=limits, floor=lambda: pet.motion.behaviour == 'floor',
                         offset=offset, appearance=appearance)
        self._last_time = monotonic()
        self._elapsed = 0.0

    def tick(self, elapsed=None):
        now = monotonic()
        dt = max(0, min(0.05, now - self._last_time if elapsed is None else elapsed))
        self._last_time = now
        self._elapsed += dt
        if self._elapsed >= 30:
            self.pet.stop_toy()
            return
        self.pet.motion.set_guidance(*self.target)
        nearby = self.pet.geometry().adjusted(-8, -8, 8, 8).contains(*map(round, self.target))
        self._near_time = self._near_time + dt if nearby and not self.dragging else 0.0
        if self._near_time >= 0.5:
            pet = self.pet
            pet.stop_toy()
            pet._interaction_feedback(pet.profile_session.request(self.arrival_action))

