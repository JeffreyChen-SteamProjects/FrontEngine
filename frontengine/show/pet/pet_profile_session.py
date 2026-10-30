"""GUI-owned identity leases and debounced persistent pet state."""
from __future__ import annotations

from time import monotonic
from weakref import WeakValueDictionary

from PySide6.QtCore import QObject, QTimer, Signal

from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.user_setting.user_setting_file import user_setting_dict, write_user_setting
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.retranslate import translate
from frontengine.utils.pet_companion import CompanionState

_ACTIVE = WeakValueDictionary()


class PetProfileSession(QObject):
    """One live session per saved identity; clones always use a fresh ID."""

    changed = Signal()

    def __init__(self, parent: QObject, identifier: str | None = None,
                 profiles: PetProfiles | None = None, name: str = "") -> None:
        super().__init__(parent)
        self.profiles = profiles or PetProfiles(user_setting_dict, write_user_setting)
        record = self.profiles.get(identifier) if identifier else self.profiles.create(name)
        self.identifier = record["id"]
        self._key = (id(self.profiles.settings), self.identifier)
        if self._key in _ACTIVE:
            raise ValueError(translate('pet_profile_active', 'This pet identity is already active; clone it to create another'))
        _ACTIVE[self._key] = self
        self._closed = False
        self.initial = record
        self.companion = CompanionState(record)
        self.mode_revision = 0
        self.appearance_renderer = None
        self._clock = monotonic
        self._last_tick = None
        self.care_timer = QTimer(self)
        self.care_timer.setInterval(100)
        self.care_timer.timeout.connect(self._tick)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.flush)

    def schedule(self) -> None:
        """Coalesce changes in the same interaction without constant disk writes."""
        if not self._closed:
            self.timer.start(500)

    def state(self) -> dict:
        """Use the latest saved name and this pet's current runtime statistics."""
        saved = self.profiles.get(self.identifier)
        return {**saved, **self.companion.snapshot()}

    def resume(self) -> None:
        """Begin active-time care without simulating time spent hidden or offline."""
        if not self._closed and not self.care_timer.isActive():
            self._last_tick = self._clock()
            self.care_timer.start()

    def pause(self) -> None:
        self.care_timer.stop()
        self._last_tick = None

    def _tick(self) -> None:
        now = self._clock()
        elapsed = now - self._last_tick if self._last_tick is not None else 0
        self._last_tick = now
        if 0 <= elapsed <= 5:
            self.advance(elapsed)

    def advance(self, seconds: float) -> None:
        if self._closed:
            return
        before = (self.companion.snapshot(), self.companion.action, self.companion.visual_action)
        self.companion.advance(seconds)
        after = (self.companion.snapshot(), self.companion.action, self.companion.visual_action)
        if before != after:
            if before[0]['mode'] != after[0]['mode']:
                self.mode_revision += 1
            if before[0] != after[0]:
                self.schedule()
            self.changed.emit()

    def request(self, action: str, kind: str = "snack") -> str:
        if self._closed:
            return "unsupported"
        result = self.companion.request(action, kind)
        if result == "accepted":
            self.changed.emit()
        return result

    def set_mode(self, mode: str) -> str:
        if self._closed:
            return "unsupported"
        result = self.companion.set_mode(mode)
        if result == "accepted":
            self.mode_revision += 1
            self.schedule()
            self.changed.emit()
        return result

    def reward(self, kind: str) -> str:
        result = "unsupported" if self._closed else self.companion.reward(kind)
        if result == "accepted":
            self.schedule()
            self.changed.emit()
        return result

    def reward_focus(self) -> bool:
        """Apply a controller-deduplicated completion to an available working pet."""
        if self._closed or self.companion.mode != 'work' or self.companion.action is not None:
            return False
        self.companion.growth.add(3)
        self.companion.mood.pet(5)
        self.schedule()
        self.changed.emit()
        return True

    def present(self, action: str) -> bool:
        if self._closed or not self.companion.present(action):
            return False
        self.changed.emit()
        return True

    def apply_appearance(self, expected: dict, candidate: dict, prepared=None, present: bool = True) -> None:
        """Persist a prevalidated/preloaded wardrobe draft without stale overwrites."""
        if self._closed:
            raise ValueError("Pet session is closed")
        saved = self.profiles.get(self.identifier)
        if saved["appearance"] != expected:
            raise ValueError("Pet appearance changed while previewing")
        self.profiles.update(self.identifier, {**self.companion.snapshot(), "appearance": candidate})
        self.appearance_renderer = prepared
        if present and candidate != expected:
            self.companion.present('outfit_show')
        self.changed.emit()

    def apply_preferences(self, expected: dict, candidate: dict) -> None:
        """Commit a detached customization draft before changing the live pet."""
        if self._closed:
            raise ValueError("Pet session is closed")
        saved = self.profiles.get(self.identifier)
        if saved["preferences"] != expected:
            raise ValueError("Pet preferences changed while editing")
        updated = self.profiles.update(self.identifier, {
            **self.companion.snapshot(), "preferences": candidate})
        self.companion.preferences = updated["preferences"]
        self.changed.emit()

    def flush(self) -> bool:
        """Save this pet only; retry failures while the widget remains alive."""
        self.timer.stop()
        try:
            state = self.state()
            saved = self.profiles.get(self.identifier)
            if state != saved:
                self.profiles.update(self.identifier, self.companion.snapshot())
            return True
        except (OSError, ValueError, KeyError) as error:
            front_engine_logger.warning(f"[PetProfile] save failed: {error!r}")
            self.timer.start(5000)
            return False

    def close(self) -> bool:
        """Release the identity only after a successful flush; retain failed writes."""
        if self._closed:
            return True
        if not self.flush():
            return False
        self.pause()
        self._closed = True
        self.appearance_renderer = None
        self.timer.stop()
        if _ACTIVE.get(self._key) is self:
            _ACTIVE.pop(self._key, None)
        return True

    @staticmethod
    def active(profiles: PetProfiles, identifier: str) -> PetProfileSession | None:
        """Return an active session for export/rename without creating a widget."""
        return _ACTIVE.get((id(profiles.settings), identifier))
