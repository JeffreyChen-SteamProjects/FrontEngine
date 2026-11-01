"""Whether the user's session is locked, and a watcher that reports when that changes.

On Windows a locked session switches input to the secure "Winlogon" desktop; the
probe asks for the name of the current input desktop and treats one it cannot open
as locked. Elsewhere the state is unknown and reported as unlocked, so nothing pauses.
The probe only reads desktop state through ctypes: no subprocess, nothing is changed.
"""
from __future__ import annotations

import sys
from typing import Callable

from PySide6.QtCore import QObject, QTimer, Signal

POLL_MS = 2000
_DESKTOP_READOBJECTS = 0x0001
_UOI_NAME = 2


def is_session_locked() -> bool:
    if sys.platform != "win32":
        return False
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.OpenInputDesktop.restype = wintypes.HANDLE
    user32.OpenInputDesktop.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    user32.GetUserObjectInformationW.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                                  wintypes.DWORD, ctypes.POINTER(wintypes.DWORD))
    user32.CloseDesktop.argtypes = (wintypes.HANDLE,)
    desktop = user32.OpenInputDesktop(0, False, _DESKTOP_READOBJECTS)
    if not desktop:
        return True                      # the secure desktop cannot be opened from the user session
    try:
        name = ctypes.create_unicode_buffer(256)
        needed = wintypes.DWORD(0)
        if not user32.GetUserObjectInformationW(desktop, _UOI_NAME, name, ctypes.sizeof(name), ctypes.byref(needed)):
            return False
        return name.value.lower() == "winlogon"
    finally:
        user32.CloseDesktop(desktop)


class SessionLockWatcher(QObject):
    """Polls the lock state on the GUI thread and emits ``locked_changed`` on each change."""

    locked_changed = Signal(bool)

    def __init__(self, parent: QObject | None = None, probe: Callable[[], bool] | None = None,
                 interval_ms: int = POLL_MS) -> None:
        super().__init__(parent)
        self.probe = probe
        self.locked = False
        self.timer = QTimer(self)
        self.timer.setInterval(interval_ms)
        self.timer.timeout.connect(self.check)

    def start(self) -> None:
        self.check()
        self.timer.start()

    def stop(self) -> None:
        self.timer.stop()

    def check(self) -> bool:
        try:
            locked = bool((self.probe or is_session_locked)())     # looked up now, so tests can stand it in
        except OSError:
            locked = False               # an unreadable state never pauses anything
        if locked != self.locked:
            self.locked = locked
            self.locked_changed.emit(locked)
        return locked
