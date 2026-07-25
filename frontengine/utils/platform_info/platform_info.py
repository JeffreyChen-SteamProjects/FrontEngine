"""
跨平台的系統狀態偵測：使用者閒置時間、電池、可站立的視窗上緣。
Windows 走 ctypes，Linux 走 X11／/sys，macOS 走系統內建指令；任何平台取不到
都回傳 None／空清單，不新增相依套件。解析部分是純函式，方便測試。

Cross-platform system probes: user idle time, battery, and standable window
edges. Windows uses ctypes, Linux uses X11 and /sys, macOS shells out to
built-in tools; anything unavailable degrades to None or an empty list. No new
dependencies, and the parsing is pure so it can be tested anywhere.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from frontengine.utils.logging.loggin_instance import front_engine_logger

_COMMAND_TIMEOUT = 3
# 桌面／工作列等外殼視窗類別，不視為可站立的程式視窗
# Shell windows (desktop / taskbar) that must not count as standable.
_PLATFORM_SKIP_CLASSES = {"WorkerW", "Progman", "Shell_TrayWnd", "Button"}
_MIN_WINDOW_WIDTH = 80
_MIN_WINDOW_HEIGHT = 40


def run_command(command: List[str]) -> Optional[str]:
    """
    執行唯讀的系統指令並回傳輸出；指令不存在、逾時或失敗回傳 None。
    永遠使用 list 形式、不經 shell（不接受使用者輸入）。
    Run a read-only system command, returning its output or None. Always list
    form, never a shell — these commands take no user input.
    """
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell, no user input
            command, capture_output=True, text=True, timeout=_COMMAND_TIMEOUT, check=False)
    except (OSError, subprocess.SubprocessError) as error:
        front_engine_logger.debug(f"[platform_info] {command[0]} unavailable: {error!r}")
        return None
    return completed.stdout if completed.returncode == 0 else None


# --- idle time ------------------------------------------------------------
def parse_macos_idle(output: str) -> Optional[float]:
    """
    從 `ioreg -c IOHIDSystem` 的輸出取出閒置秒數（HIDIdleTime 為奈秒）。
    Pull idle seconds out of `ioreg -c IOHIDSystem` (HIDIdleTime is nanoseconds).
    """
    for line in str(output or "").splitlines():
        if "HIDIdleTime" not in line:
            continue
        digits = "".join(character for character in line.split("=")[-1] if character.isdigit())
        if digits:
            return int(digits) / 1_000_000_000.0
    return None


def idle_seconds() -> Optional[float]:
    """使用者未操作的秒數；取不到回傳 None / Seconds since the last user input."""
    if sys.platform == "win32":
        return _idle_seconds_windows()
    if sys.platform == "darwin":
        output = run_command(["ioreg", "-c", "IOHIDSystem"])
        return parse_macos_idle(output) if output else None
    return _idle_seconds_x11()


def _idle_seconds_windows() -> Optional[float]:
    try:
        import ctypes

        class _LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        info = _LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(info)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            return None
        elapsed_ms = ctypes.windll.kernel32.GetTickCount() - info.dwTime
        return max(0.0, elapsed_ms / 1000.0)
    except Exception as error:  # pragma: no cover - Win32 boundary
        front_engine_logger.debug(f"[platform_info] GetLastInputInfo failed: {error!r}")
        return None


def _idle_seconds_x11() -> Optional[float]:
    """透過 X11 的 XScreenSaver 擴充取得閒置毫秒數（需要 X 顯示）。"""
    try:
        import ctypes

        class _XScreenSaverInfo(ctypes.Structure):
            _fields_ = [
                ("window", ctypes.c_ulong), ("state", ctypes.c_int), ("kind", ctypes.c_int),
                ("since", ctypes.c_ulong), ("idle", ctypes.c_ulong), ("event_mask", ctypes.c_ulong),
            ]

        x11 = ctypes.cdll.LoadLibrary("libX11.so.6")
        screensaver = ctypes.cdll.LoadLibrary("libXss.so.1")
        x11.XOpenDisplay.restype = ctypes.c_void_p
        display = x11.XOpenDisplay(None)
        if not display:
            return None
        try:
            screensaver.XScreenSaverAllocInfo.restype = ctypes.POINTER(_XScreenSaverInfo)
            info = screensaver.XScreenSaverAllocInfo()
            root = x11.XDefaultRootWindow(ctypes.c_void_p(display))
            if not screensaver.XScreenSaverQueryInfo(ctypes.c_void_p(display), root, info):
                return None
            return max(0.0, info.contents.idle / 1000.0)
        finally:
            x11.XCloseDisplay(ctypes.c_void_p(display))
    except Exception as error:
        front_engine_logger.debug(f"[platform_info] X11 idle unavailable: {error!r}")
        return None


# --- battery --------------------------------------------------------------
def parse_macos_battery(output: str) -> Optional[Tuple[int, bool]]:
    """從 `pmset -g batt` 取出 (電量百分比, 是否充電中)。"""
    text = str(output or "")
    if "%" not in text:
        return None
    percent_text = text.split("%")[0].split()[-1].strip().rstrip(";")
    try:
        percent = int(percent_text)
    except ValueError:
        return None
    # 狀態字接在百分比後面，例如 "87%; discharging; 3:12 remaining"。
    # 不能直接找 "charging"，因為 "discharging" 也含有它。
    # The state word follows the percentage ("87%; discharging; …"). Don't
    # substring-match "charging" — "discharging" contains it.
    tail = text.split("%", 1)[1].lower()
    parts = [part.strip() for part in tail.split(";") if part.strip()]
    state = parts[0] if parts else ""
    charging = state != "discharging" if state else "ac power" in text.lower()
    return (max(0, min(100, percent)), charging)


def read_linux_battery(root: str = "/sys/class/power_supply") -> Optional[Tuple[int, bool]]:
    """從 /sys 讀第一顆電池的 (電量百分比, 是否充電中)。"""
    try:
        base = Path(root)
        for entry in sorted(base.iterdir()):
            capacity_file = entry / "capacity"
            if not capacity_file.is_file():
                continue
            percent = int(capacity_file.read_text(encoding="utf-8").strip())
            status_file = entry / "status"
            status = status_file.read_text(encoding="utf-8").strip() if status_file.is_file() else ""
            return (max(0, min(100, percent)), status.lower() != "discharging")
    except (OSError, ValueError) as error:
        front_engine_logger.debug(f"[platform_info] /sys battery unavailable: {error!r}")
    return None


def read_battery() -> Optional[Tuple[int, bool]]:
    """回傳 (電量百分比, 是否充電中)；沒有電池或取不到回傳 None。"""
    if sys.platform == "win32":
        return _read_battery_windows()
    if sys.platform == "darwin":
        output = run_command(["pmset", "-g", "batt"])
        return parse_macos_battery(output) if output else None
    return read_linux_battery()


def _read_battery_windows() -> Optional[Tuple[int, bool]]:
    try:
        import ctypes

        class _SPS(ctypes.Structure):
            _fields_ = [
                ("ACLineStatus", ctypes.c_byte), ("BatteryFlag", ctypes.c_byte),
                ("BatteryLifePercent", ctypes.c_byte), ("SystemStatusFlag", ctypes.c_byte),
                ("BatteryLifeTime", ctypes.c_ulong), ("BatteryFullLifeTime", ctypes.c_ulong),
            ]

        status = _SPS()
        if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
            return None
        percent = status.BatteryLifePercent & 0xFF
        if percent == 255:  # unknown / no battery
            return None
        return (int(percent), status.ACLineStatus == 1)
    except Exception as error:  # pragma: no cover - Win32 boundary
        front_engine_logger.debug(f"[platform_info] GetSystemPowerStatus failed: {error!r}")
        return None


# --- standable windows ----------------------------------------------------
def parse_wmctrl_geometry(output: str) -> List[Tuple[int, int, int]]:
    """
    把 `wmctrl -lG` 的輸出轉成可站立平台 (left, right, top_y)。
    Turn `wmctrl -lG` output into standable platforms (left, right, top_y).
    """
    platforms: List[Tuple[int, int, int]] = []
    for line in str(output or "").splitlines():
        fields = line.split(None, 7)
        if len(fields) < 7:
            continue
        try:
            left, top, width, height = (int(fields[index]) for index in (2, 3, 4, 5))
        except ValueError:
            continue
        if width < _MIN_WINDOW_WIDTH or height < _MIN_WINDOW_HEIGHT:
            continue
        platforms.append((left, left + width, top))
    return platforms


def standable_windows(exclude_handles=()) -> List[Tuple[int, int, int]]:
    """
    回傳可站立的視窗上緣 (left, right, top_y)。Windows 列舉頂層視窗，Linux 走
    wmctrl（沒安裝就回空），macOS 目前沒有免相依的做法，回傳空清單。
    """
    if sys.platform == "win32":
        return _standable_windows_windows(exclude_handles)
    if sys.platform == "darwin":
        return []  # needs a native API binding; degrades to "floor only"
    output = run_command(["wmctrl", "-lG"])
    return parse_wmctrl_geometry(output) if output else []


def _standable_windows_windows(exclude_handles=()) -> List[Tuple[int, int, int]]:
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        exclude = {int(handle) for handle in exclude_handles}
        platforms: List[Tuple[int, int, int]] = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def _collect(hwnd, _lparam):
            if int(hwnd) in exclude or not user32.IsWindowVisible(hwnd):
                return True
            rect = wintypes.RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return True
            if rect.right - rect.left < _MIN_WINDOW_WIDTH or rect.bottom - rect.top < _MIN_WINDOW_HEIGHT:
                return True
            class_buffer = ctypes.create_unicode_buffer(64)
            user32.GetClassNameW(hwnd, class_buffer, 64)
            if class_buffer.value in _PLATFORM_SKIP_CLASSES:
                return True
            platforms.append((rect.left, rect.right, rect.top))
            return True

        user32.EnumWindows(_collect, 0)
        return platforms
    except Exception as error:  # pragma: no cover - Win32 boundary
        front_engine_logger.warning(f"[platform_info] EnumWindows failed: {error!r}")
        return []
