"""One monotonic animation clock shared by a scene's visible views."""
from __future__ import annotations

from copy import deepcopy
import math
import time
from typing import Callable

from PySide6.QtCore import QObject, QTimer, Signal

from frontengine.utils.scene_format.scene_animation import animation_duration, sample_animation, validate_animation


class SceneTimeline(QObject):
    """Preview/playback use the same interpolation; pauses never advance time."""

    changed = Signal(float)
    state_changed = Signal(str)

    def __init__(self, parent: QObject, apply: Callable, *, clock: Callable = time.monotonic) -> None:
        super().__init__(parent)
        self.apply, self.clock = apply, clock
        self.entries = {}
        self.duration, self.position = 0.0, 0.0
        self.minimum_duration = 0.0
        self.state = 'stopped'
        self.active = False
        self.previewing = False
        self.requested = False
        self._anchor = 0.0
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.tick)

    def configure(self, entries: dict, *, reset: bool = False) -> None:
        """Replace validated tracks, preserving playback time unless editing a preview."""
        for entry in entries.values():
            validate_animation(entry.get('animation', []))
        self.entries = deepcopy(entries)
        self.duration = max(self.minimum_duration, animation_duration(entries))
        if reset:
            self.reset()
        elif self.previewing:
            self.position = min(self.position, self.duration)
            self._anchor = self.clock() - self.position
            self._apply()

    def _state(self, state: str) -> None:
        self.state = state
        self.state_changed.emit(state)

    def _apply(self) -> None:
        stamp = self.position if self.previewing else None
        self.apply({key: sample_animation(entry, stamp) for key, entry in self.entries.items()})
        self.changed.emit(self.position)

    def play(self, *, restart: bool = False) -> None:
        """Start or resume; replay explicitly resets the clock to zero."""
        if restart or self.position >= self.duration:
            self.position = 0.0
        self.requested, self.previewing = True, True
        self._anchor = self.clock() - self.position
        self._state('playing' if self.active else 'paused')
        if self.active and self.duration > 0:
            self.timer.start()
        self._apply()

    def pause(self) -> None:
        """Pause at the current effective position until explicit resume."""
        if self.timer.isActive():
            self.tick()
        self.timer.stop()
        self.requested = False
        self._state('paused')

    def seek(self, seconds: float) -> None:
        """Scrub without changing the saved scene or requesting playback."""
        if type(seconds) not in (int, float) or not math.isfinite(seconds):
            raise ValueError('Timeline position must be finite')
        self.timer.stop()
        self.position = max(0, min(self.duration, seconds))
        self.requested, self.previewing = False, True
        self._state('paused')
        self._apply()

    def tick(self) -> None:
        """Sample from monotonic elapsed time, independent of missed timer events."""
        if not self.active or not self.requested:
            return
        self.position = min(self.duration, max(0, self.clock() - self._anchor))
        self._apply()
        if self.position >= self.duration:
            self.timer.stop()
            self.requested = False
            self._state('finished')

    def set_active(self, active: bool) -> None:
        """Suspend the clock while all views are hidden, preserving user pause."""
        if self.active == active:
            return
        if not active:
            self.tick()
            self.timer.stop()
        self.active = active
        if self.requested:
            self._anchor = self.clock() - self.position
            self._state('playing' if active else 'paused')
            if active and self.duration > 0:
                self.timer.start()

    def reset(self) -> None:
        """Stop preview and restore saved layer properties."""
        self.timer.stop()
        self.position = 0.0
        self.requested, self.previewing = False, False
        self._state('stopped')
        self._apply()

    def shutdown(self) -> None:
        """Release timer, tracks and callback before their scene is destroyed."""
        self.timer.stop()
        self.requested = False
        self.entries.clear()
        self.apply = lambda _values: None
