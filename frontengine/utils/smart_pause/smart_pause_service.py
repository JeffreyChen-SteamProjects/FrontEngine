from __future__ import annotations

import sys
from typing import Callable, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.platform_info.platform_info import active_app_name, read_battery
from frontengine.utils.smart_pause.pause_rules import DEFAULT_RULES, pause_reason

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


def battery_detector() -> bool:
    """
    是否正在用電池供電。讀不到電池狀態（桌機、權限不足）一律當作插著電，
    因為「不確定」時不該擅自把使用者的覆蓋層收起來。
    Whether the machine is running on battery. When the battery cannot be read
    at all - a desktop, or a refused probe - report False: not knowing is not a
    reason to take the user's overlays away.
    """
    reading = read_battery()
    if reading is None:
        return False
    _percent, charging = reading
    return not charging


class SmartPauseService(QObject):
    """
    以 QTimer 週期性檢查三件事：前景是不是全螢幕程式、是不是改吃電池、
    前景程式有沒有在使用者指定的清單裡。任何一條規則成立就發出暫停訊號，
    讓主視窗暫時收起覆蓋層。三個偵測函式與規則來源都可注入以利測試。

    Poll three things on a QTimer: is a fullscreen app in front, did the machine
    move to battery power, and does the focused app appear in the user's list.
    When any enabled rule fires, emit a pause signal so the main window can
    stand the overlays down. Every probe and the rule source are injectable.
    """

    # (是否暫停, 原因)；恢復時原因為空字串
    # (paused, reason); the reason is an empty string when resuming.
    pause_changed = Signal(bool, str)

    def __init__(
        self,
        detector: Optional[Callable[[], bool]] = None,
        interval_ms: int = 2000,
        parent: Optional[QObject] = None,
        battery_provider: Optional[Callable[[], bool]] = None,
        app_provider: Optional[Callable[[], Optional[str]]] = None,
        rules_provider: Optional[Callable[[], dict]] = None,
    ) -> None:
        super().__init__(parent)
        self._detector: Callable[[], bool] = detector or windows_fullscreen_detector
        self._battery_provider: Callable[[], bool] = battery_provider or battery_detector
        self._app_provider: Callable[[], Optional[str]] = app_provider or active_app_name
        self._rules_provider: Callable[[], dict] = rules_provider or (lambda: DEFAULT_RULES)
        self._active: bool = False
        self._reason: str = ""
        self._timer = QTimer(self)
        self._timer.setInterval(max(250, int(interval_ms)))
        self._timer.timeout.connect(self._poll)

    @property
    def active(self) -> bool:
        return self._active

    @property
    def reason(self) -> str:
        """目前這次暫停的原因；沒有暫停時是空字串。"""
        return self._reason

    def start(self) -> None:
        front_engine_logger.info("[SmartPause] start")
        self._timer.start()

    def stop(self) -> None:
        front_engine_logger.info("[SmartPause] stop")
        self._timer.stop()

    def _current_rules(self) -> dict:
        try:
            rules = self._rules_provider()
        except Exception as error:  # pragma: no cover - defensive boundary
            front_engine_logger.warning(f"[SmartPause] rules error: {error!r}")
            return DEFAULT_RULES
        return rules if isinstance(rules, dict) else DEFAULT_RULES

    def _poll(self) -> None:
        rules = self._current_rules()
        # 只在規則真的會用到時才去問，省下每次輪詢的系統呼叫
        # Only probe what the enabled rules actually need, to keep each poll cheap.
        try:
            fullscreen = bool(self._detector()) if rules.get("fullscreen", True) else False
            on_battery = bool(self._battery_provider()) if rules.get("battery", False) else False
            active_app = self._app_provider() if rules.get("apps") else None
        except Exception as error:  # pragma: no cover - defensive boundary
            front_engine_logger.warning(f"[SmartPause] poll error: {error!r}")
            return
        reason = pause_reason(rules, fullscreen=fullscreen,
                              on_battery=on_battery, active_app=active_app) or ""
        now = bool(reason)
        if now != self._active:
            self._active = now
            self._reason = reason
            front_engine_logger.info(f"[SmartPause] {'pause' if now else 'resume'} | {reason or '-'}")
            self.pause_changed.emit(now, reason)
        elif now and reason != self._reason:
            # 仍在暫停，但換了原因（例如全螢幕結束但改吃電池）
            # Still paused, but for a different reason now.
            self._reason = reason

    def poll_once(self) -> None:
        """Run a single poll immediately (used by tests)."""
        self._poll()
