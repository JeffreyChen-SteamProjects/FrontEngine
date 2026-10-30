"""Autonomous strolling for Puppet pets: short walks along the current height, with rests between."""
from __future__ import annotations

import random
from time import monotonic

from PySide6.QtCore import QObject, QTimer


class PuppetStroll(QObject):
    """Walk the pet left or right now and then while nothing else is moving it.

    It yields to everything that already owns the pet: dragging, petting, a call or
    toy target, settling while typing and companion modes without autonomy. The
    pet ends every walk inside its screen's work area.
    """

    SPEED = 70.0              # pixels per second
    REST_SECONDS = (3.0, 8.0)
    DISTANCE = (120, 420)     # pixels per walk

    def __init__(self, pet, rng: random.Random | None = None) -> None:
        super().__init__(pet)
        self.pet = pet
        self.rng = rng or random.Random()  # nosec B311 - stroll timing and distance only, not security
        self.walking = False
        self.target_x: int | None = None
        self._x = 0.0
        self._last = monotonic()
        self._rest = QTimer(self)
        self._rest.setSingleShot(True)
        self._rest.timeout.connect(self._begin)
        self._step = QTimer(self)
        self._step.setInterval(33)
        self._step.timeout.connect(self.tick)

    def _free(self) -> bool:
        return self.pet.can_play_with_toy and self.pet._target.marker is None

    def _span(self) -> tuple[int, int] | None:
        screen = self.pet.screen()
        if screen is None:
            return None
        area = screen.availableGeometry()
        left, right = area.left(), area.right() + 1 - self.pet.width()
        return (left, right) if right > left else None

    def start(self) -> None:
        """Schedule the next walk unless one is already waiting or under way."""
        if not self.walking and not self._rest.isActive():
            self._rest.start(round(1000 * self.rng.uniform(*self.REST_SECONDS)))

    def stop(self) -> None:
        """Stop walking and waiting; nothing resumes until start() is called."""
        self._rest.stop()
        self._step.stop()
        if self.walking:
            self.walking = False
            self.target_x = None
            self.pet._show_activity()

    def _begin(self) -> None:
        span = self._span()
        if not self._free() or span is None:
            self.start()
            return
        left, right = span
        distance = self.rng.randint(*self.DISTANCE)
        x = self.pet.x()
        options = [min(max(x + sign * distance, left), right) for sign in self.rng.sample((-1, 1), 2)]
        target = next((option for option in options if abs(option - x) >= 20), None)
        if target is None:
            self.start()
            return
        self.target_x, self._x, self._last = target, float(x), monotonic()
        self.walking = True
        self._step.start()
        self.pet._show_activity()

    def tick(self, elapsed: float | None = None) -> None:
        if not self.walking:
            return
        if not self._free():
            self._finish()
            return
        now = monotonic()
        dt = max(0.0, min(0.05, now - self._last if elapsed is None else elapsed))
        self._last = now
        remaining = self.target_x - self._x
        step = min(abs(remaining), self.SPEED * dt)
        self._x += step if remaining > 0 else -step
        self.pet.move(round(self._x), self.pet.y())
        if abs(self.target_x - self._x) < 0.5:
            self._finish()

    def _finish(self) -> None:
        self._step.stop()
        self.walking = False
        self.target_x = None
        self.pet._show_activity()
        if not self.pet._closed and self.pet.isVisible() and not self.pet._settled:
            self.start()
