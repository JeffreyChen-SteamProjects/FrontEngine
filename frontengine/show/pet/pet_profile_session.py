"""GUI-owned identity leases and debounced persistent pet state."""
from __future__ import annotations

from typing import Callable
from weakref import WeakValueDictionary

from PySide6.QtCore import QObject, QTimer

from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.user_setting.user_setting_file import user_setting_dict, write_user_setting
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.retranslate import translate

_ACTIVE = WeakValueDictionary()


class PetProfileSession(QObject):
    """One live session per saved identity; clones always use a fresh ID."""

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
        self.reader: Callable[[], dict] = lambda: self.profiles.get(self.identifier)
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
        return {**saved, **self.reader(), "id": self.identifier, "name": saved["name"]}

    def flush(self) -> bool:
        """Save this pet only; retry failures while the widget remains alive."""
        self.timer.stop()
        try:
            state = self.state()
            saved = self.profiles.get(self.identifier)
            if state != saved:
                self.profiles.update(self.identifier, {key: state[key] for key in ("mood", "fullness", "affection")})
            return True
        except (OSError, ValueError, KeyError) as error:
            front_engine_logger.warning(f"[PetProfile] save failed: {error!r}")
            self.timer.start(5000)
            return False

    def close(self) -> None:
        """Flush before releasing the identity and stop every persistence timer."""
        if self._closed:
            return
        self.flush()
        self._closed = True
        self.timer.stop()
        if _ACTIVE.get(self._key) is self:
            _ACTIVE.pop(self._key, None)

    @staticmethod
    def active(profiles: PetProfiles, identifier: str) -> PetProfileSession | None:
        """Return an active session for export/rename without creating a widget."""
        return _ACTIVE.get((id(profiles.settings), identifier))
