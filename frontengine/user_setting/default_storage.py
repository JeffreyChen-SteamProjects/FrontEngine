"""One captured settings binding shared by explicitly admitted default scopes."""
from __future__ import annotations

import os
from pathlib import Path
from threading import RLock

from frontengine.user_setting.storage_session import StorageBusy, StorageClosed, StorageInUse, StorageSession

_mutex = RLock()
_pid = os.getpid()
_owner: StorageSession | None = None
_bindings: set[_DefaultBindingUse] = set()
_retiring = False


def _check_pid() -> None:
    if _pid != os.getpid():
        raise StorageClosed('Default settings ownership cannot be inherited by a child process')


class _DefaultBindingUse:
    def __init__(self, storage: StorageSession) -> None:
        self.storage = storage
        self._use = storage._hold('default scope')
        self._closed = False

    def close(self) -> bool:
        """Release this scope, retaining the last binding until all clients finish."""
        global _owner, _retiring
        _check_pid()
        self.storage._check_pid()
        with _mutex:
            if self._closed:
                return True
            self._use.release()
            if len(_bindings) == 1:
                _retiring = True
                try:
                    self.storage.close()
                except StorageBusy:
                    return False
                _owner = None
                _retiring = False
            _bindings.remove(self)
            self._closed = True
            return True


def acquire_default_binding() -> _DefaultBindingUse:
    """Acquire before first global read; repeated live scopes never reload settings."""
    global _owner
    _check_pid()
    current = _owner
    if current is not None:
        current._check_pid()
    with _mutex:
        if _retiring:
            raise StorageInUse('Default settings are still retiring')
        directory = Path.cwd().resolve()
        if _owner is not None and _owner.directory != directory:
            raise StorageInUse('A different default settings directory is already active')
        if _owner is None:
            from frontengine.user_setting.user_setting_file import user_setting_dict
            owner = StorageSession.open(directory)
            try:
                snapshot = owner.settings
                user_setting_dict.clear()
                user_setting_dict.update(snapshot)
                owner._settings = user_setting_dict
                token = _DefaultBindingUse(owner)
            except BaseException:
                owner.close()
                raise
            _owner = owner
        else:
            token = _DefaultBindingUse(_owner)
        _bindings.add(token)
        return token


def default_storage() -> StorageSession:
    """Return the admitted default owner; this lookup never opens a directory."""
    _check_pid()
    current = _owner
    if current is None:
        raise StorageClosed('Open a DefaultSettingsLifetime before accessing settings')
    current._check_pid()
    with _mutex:
        if _owner is None or _retiring:
            raise StorageClosed('Default settings are closed or retiring')
        with _owner._operation():
            return _owner
