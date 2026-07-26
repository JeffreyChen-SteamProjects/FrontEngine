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

import subprocess  # nosec B404 - only runs the fixed, read-only argv in _ALLOWED_COMMANDS
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from frontengine.utils.logging.loggin_instance import front_engine_logger

_COMMAND_TIMEOUT = 3
# 唯一允許執行的系統指令；argv 全部寫死在這裡，呼叫端只能指名，
# 不可能把使用者輸入變成命令的一部分。
# The only commands this module may run. Every argv is fixed here and callers
# pass a name, so user input can never become part of a command line.
_ALLOWED_COMMANDS = {}  # name -> runner, filled in below once the runners exist
# 只從這些固定的絕對路徑找 wmctrl，不依賴 PATH（避免被同名程式攔截）
# wmctrl is looked up in these fixed absolute locations only — never via PATH,
# which another program could shadow.
_WMCTRL_PATHS = ("/usr/bin/wmctrl", "/usr/local/bin/wmctrl", "/bin/wmctrl")
# 同樣的道理：xdotool 只從固定絕對路徑找
# Same reasoning for xdotool: fixed absolute locations only.
_XDOTOOL_PATHS = ("/usr/bin/xdotool", "/usr/local/bin/xdotool", "/bin/xdotool")
# 桌面／工作列等外殼視窗類別，不視為可站立的程式視窗
# Shell windows (desktop / taskbar) that must not count as standable.
_PLATFORM_SKIP_CLASSES = {"WorkerW", "Progman", "Shell_TrayWnd", "Button"}
_MIN_WINDOW_WIDTH = 80
_MIN_WINDOW_HEIGHT = 40


def _output_of(completed) -> Optional[str]:
    """指令成功才回傳輸出，否則 None。"""
    return completed.stdout if completed.returncode == 0 else None


def _macos_idle_output() -> Optional[str]:
    return _output_of(subprocess.run(  # nosec B603 # nosemgrep - literal absolute argv, shell=False
        ["/usr/sbin/ioreg", "-c", "IOHIDSystem"],
        capture_output=True, text=True, timeout=_COMMAND_TIMEOUT, check=False, shell=False))


def _macos_battery_output() -> Optional[str]:
    return _output_of(subprocess.run(  # nosec B603 # nosemgrep - literal absolute argv, shell=False
        ["/usr/bin/pmset", "-g", "batt"],
        capture_output=True, text=True, timeout=_COMMAND_TIMEOUT, check=False, shell=False))


def _linux_windows_output() -> Optional[str]:
    """wmctrl 各發行版安裝位置不同，只從固定的絕對路徑清單裡找，不查 PATH。"""
    for candidate in _WMCTRL_PATHS:
        if not Path(candidate).is_file():
            continue
        return _output_of(subprocess.run(  # nosec B603 # nosemgrep - absolute path from a fixed list
            [candidate, "-lG"],
            capture_output=True, text=True, timeout=_COMMAND_TIMEOUT, check=False, shell=False))
    return None


def _macos_front_app_output() -> Optional[str]:
    """問 System Events 目前最前面的程式叫什麼名字（argv 全部寫死）。"""
    return _output_of(subprocess.run(  # nosec B603 # nosemgrep - literal absolute argv, shell=False
        ["/usr/bin/osascript", "-e",
         'tell application "System Events" to get name of first application process '
         'whose frontmost is true'],
        capture_output=True, text=True, timeout=_COMMAND_TIMEOUT, check=False, shell=False))


def _linux_front_app_output() -> Optional[str]:
    """xdotool 各發行版位置不同，只從固定的絕對路徑清單裡找，不查 PATH。"""
    for candidate in _XDOTOOL_PATHS:
        if not Path(candidate).is_file():
            continue
        return _output_of(subprocess.run(  # nosec B603 # nosemgrep - absolute path from a fixed list
            [candidate, "getactivewindow", "getwindowclassname"],
            capture_output=True, text=True, timeout=_COMMAND_TIMEOUT, check=False, shell=False))
    return None


_ALLOWED_COMMANDS.update({
    "macos_idle": _macos_idle_output,
    "macos_battery": _macos_battery_output,
    "linux_windows": _linux_windows_output,
    "macos_front_app": _macos_front_app_output,
    "linux_front_app": _linux_front_app_output,
})


def run_command(name: str) -> Optional[str]:
    """
    執行白名單內的唯讀系統指令並回傳輸出；名稱不在白名單、指令不存在、逾時或
    失敗都回傳 None。每個指令的 argv 寫死在各自的函式裡，呼叫端只能指名，
    使用者輸入不可能變成命令的一部分，也不經過 shell。

    Run one of the allowlisted read-only commands and return its output, or
    None. Each command's argv is a literal inside its own function and callers
    only pass a name, so user input can never become part of a command line —
    and nothing goes through a shell.
    """
    runner = _ALLOWED_COMMANDS.get(name)
    if runner is None:
        front_engine_logger.warning(f"[platform_info] refusing unknown command: {name!r}")
        return None
    try:
        return runner()
    except (OSError, subprocess.SubprocessError) as error:
        front_engine_logger.debug(f"[platform_info] {name} unavailable: {error!r}")
        return None


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
        output = run_command("macos_idle")
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
        output = run_command("macos_battery")
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
    output = run_command("linux_windows")
    return parse_wmctrl_geometry(output) if output else []


def _standable_windows_windows(exclude_handles=()) -> List[Tuple[int, int, int]]:
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        exclude = {int(handle) for handle in exclude_handles}
        platforms: List[Tuple[int, int, int]] = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        # EnumWindows 的回呼一定要回傳 True 才會繼續列舉；回 False 會中途停下。
        # 所以「永遠回傳同一個值」在這裡是規格要求，不是漏寫。
        # An EnumWindows callback must return True to keep enumerating; False
        # stops it early. Always returning the same value is the contract
        # here, not an oversight.
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


# --- foreground application ------------------------------------------------
def parse_front_app_output(output: Optional[str]) -> Optional[str]:
    """
    把 osascript／xdotool 的輸出整理成單一程式名稱；空輸出回傳 None。
    Reduce the osascript / xdotool output to a single app name, or None.
    """
    if not output:
        return None
    first_line = output.strip().splitlines()[0].strip() if output.strip() else ""
    return first_line or None


def active_app_name() -> Optional[str]:
    """
    目前前景程式的名稱（Windows 走 ctypes，macOS 走 osascript，Linux 走
    xdotool）。取不到就回傳 None，呼叫端要能接受「不知道」這個答案。
    The name of the app that currently has focus. Windows uses ctypes, macOS
    asks System Events, Linux asks xdotool. Returns None when it cannot be
    determined - callers must cope with not knowing.
    """
    if sys.platform == "win32":
        return _active_app_name_windows()
    if sys.platform == "darwin":
        return parse_front_app_output(run_command("macos_front_app"))
    return parse_front_app_output(run_command("linux_front_app"))


def _active_app_name_windows() -> Optional[str]:
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return None
        # PROCESS_QUERY_LIMITED_INFORMATION：只問名字，不要求更多權限
        # PROCESS_QUERY_LIMITED_INFORMATION: ask for the name, nothing more.
        handle = kernel32.OpenProcess(0x1000, False, pid.value)
        if not handle:
            return None
        try:
            size = wintypes.DWORD(260)
            buffer = ctypes.create_unicode_buffer(size.value)
            if not kernel32.QueryFullProcessImageNameW(
                    handle, 0, buffer, ctypes.byref(size)):
                return None
            return Path(buffer.value).name or None
        finally:
            kernel32.CloseHandle(handle)
    except Exception as error:  # pragma: no cover - Win32 boundary
        front_engine_logger.warning(f"[platform_info] foreground app failed: {error!r}")
        return None
