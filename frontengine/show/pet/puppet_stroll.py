"""Autonomous behaviour for Puppet pets: after each rest, a short walk or a random action."""
from __future__ import annotations

import random
from time import monotonic

from PySide6.QtCore import QObject, QTimer


class PuppetStroll(QObject):
    """Now and then walk the pet left or right, or play a random action in place.

    It yields to everything that already owns the pet: dragging, petting, a call or
    toy target, settling while typing and companion modes without autonomy. The
    pet ends every walk inside its screen's work area.
    """

    SPEED = 70.0              # pixels per second
    REST_SECONDS = (3.0, 8.0)
    DISTANCE = (120, 420)     # pixels per walk
    # What the pet does after each rest, picked at random: (action, weight).
    CHOICES = (('walk', 50), ('sit', 12), ('play', 10), ('groom', 9), ('greet', 10), ('celebrate', 9))
    HOLD_SECONDS = {'groom': (3.0, 3.0)}   # others hold 2-4 s

    def __init__(self, pet, rng: random.Random | None = None) -> None:
        super().__init__(pet)
        self.pet = pet
        self.rng = rng or random.Random()  # nosec B311 - stroll timing and distance only, not security
        self.walking = False
        self.acting: str | None = None   # action played in place
        self._walk_next = False           # a newly summoned pet walks off first
        self._hold = 0.0
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

    def start(self, soon: bool = False) -> None:
        """Schedule the next walk or action unless one is already waiting or under way.

        ``soon`` is for a pet that was just summoned: it sets off walking almost at once.
        """
        if not self.walking and self.acting is None and not self._rest.isActive():
            self._walk_next = soon
            self._rest.start(300 if soon else round(1000 * self.rng.uniform(*self.REST_SECONDS)))

    def stop(self) -> None:
        """Stop walking, acting and waiting; nothing resumes until start() is called."""
        self._rest.stop()
        self._step.stop()
        if self.walking or self.acting is not None:
            self.walking, self.acting, self.target_x = False, None, None
            self.pet._show_activity()

    def _choose(self) -> str:
        names = [name for name, _weight in self.CHOICES]
        return self.rng.choices(names, weights=[weight for _name, weight in self.CHOICES])[0]

    def _act(self, action: str) -> None:
        """Play one action in place for its hold time."""
        self.acting = action
        self._hold = self.rng.uniform(*self.HOLD_SECONDS.get(action, (2.0, 4.0)))
        self._last = monotonic()
        self._step.start()
        self.pet._show_activity()

    def _begin(self) -> None:
        span = self._span()
        if not self._free() or span is None:
            self.start()
            return
        choice = 'walk' if self._walk_next else self._choose()
        self._walk_next = False
        if choice != 'walk':
            self._act(choice)
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
        if not self.walking and self.acting is None:
            return
        if not self._free():
            self._finish()
            return
        now = monotonic()
        dt = max(0.0, min(0.05, now - self._last if elapsed is None else elapsed))
        self._last = now
        if self.acting is not None:
            self._hold -= dt
            if self._hold <= 0:
                self._finish()
            return
        remaining = self.target_x - self._x
        step = min(abs(remaining), self.SPEED * dt)
        self._x += step if remaining > 0 else -step
        self.pet.move(round(self._x), self.pet.y())
        if abs(self.target_x - self._x) < 0.5:
            self._finish()

    def _finish(self) -> None:
        self._step.stop()
        self.walking, self.acting, self.target_x = False, None, None
        self.pet._show_activity()
        if not self.pet._closed and self.pet.isVisible() and not self.pet._settled:
            self.start()
