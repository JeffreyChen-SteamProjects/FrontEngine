from __future__ import annotations

import sys
from typing import Callable, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from frontengine.utils.logging.loggin_instance import front_engine_logger

# 桌面／工作列等外殼視窗類別，不視為全螢幕程式
# Shell windows (desktop / taskbar) that must not count as a fullscreen app.
_SHELL_WINDOW_CLASSES = {"WorkerW", "Progman", "Shell_TrayWnd", "Button"}


def windows_fullscreen_detector() -> bool:
    """
    偵測前景視窗是否為全螢幕程式（例如遊戲）。僅在 Windows 有效，其餘平台
    一律回傳 False。任何 Win32 呼叫失敗都會被吞下並回傳 False，避免崩潰。
    Detect whether the foreground window is a fullscreen app (e.g. a game).
    Windows only; other platforms always return False. Any Win32 failure is
    swallowed and reported as False so polling can never crash.
    """
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False

        class_buffer = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_buffer, 256)
        if class_buffer.value in _SHELL_WINDOW_CLASSES:
            return False

        window_rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(window_rect)):
            return False

        monitor = user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT),
                ("dwFlags", wintypes.DWORD),
            ]

        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            return False

        screen = info.rcMonitor
        return (
            window_rect.left <= screen.left
            and window_rect.top <= screen.top
            and window_rect.right >= screen.right
            and window_rect.bottom >= screen.bottom
        )
    except Exception as error:  # pragma: no cover - defensive Win32 boundary
        front_engine_logger.warning(f"[SmartPause] detector error: {error!r}")
        return False


class SmartPauseService(QObject):
    """
    以 QTimer 週期性輪詢前景視窗，當全螢幕程式出現／消失時發出訊號，讓
    主視窗可暫時隱藏覆蓋層（節省資源、避免干擾遊戲）。偵測函式可注入以
    利測試。
    Poll the foreground window on a QTimer and emit a signal when a
    fullscreen app appears / disappears, so the main window can temporarily
    hide overlays. The detector is injectable for testing.
    """

    fullscreen_changed = Signal(bool)  # True when a fullscreen app is active

    def __init__(
        self,
        detector: Optional[Callable[[], bool]] = None,
        interval_ms: int = 2000,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._detector: Callable[[], bool] = detector or windows_fullscreen_detector
        self._active: bool = False
        self._timer = QTimer(self)
        self._timer.setInterval(max(250, int(interval_ms)))
        self._timer.timeout.connect(self._poll)

    @property
    def active(self) -> bool:
        return self._active

    def start(self) -> None:
        front_engine_logger.info("[SmartPause] start")
        self._timer.start()

    def stop(self) -> None:
        front_engine_logger.info("[SmartPause] stop")
        self._timer.stop()

    def _poll(self) -> None:
        try:
            now = bool(self._detector())
        except Exception as error:  # pragma: no cover - defensive boundary
            front_engine_logger.warning(f"[SmartPause] poll error: {error!r}")
            return
        if now != self._active:
            self._active = now
            self.fullscreen_changed.emit(now)

    def poll_once(self) -> None:
        """Run a single poll immediately (used by tests)."""
        self._poll()
