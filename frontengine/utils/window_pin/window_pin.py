"""
把別人的視窗釘在最上層、或調整它的透明度。僅 Windows 有效（用 Win32 的
SetWindowPos 與分層視窗），其他平台一律回報「做不到」而不是假裝成功。

這隻模組只改視窗的顯示屬性——置頂與透明度——不注入程式碼、不讀取內容、
也不模擬輸入。

Pin someone else's window on top, or make it see-through. Windows only, via
Win32 SetWindowPos and layered windows; every other platform reports "not
supported" rather than pretending it worked.

This module only changes display attributes - stacking and opacity. It injects
nothing, reads no window content, and synthesises no input.
"""
from __future__ import annotations

import sys
from typing import List, Optional, Tuple

from frontengine.utils.logging.loggin_instance import front_engine_logger

MIN_OPACITY_PERCENT = 20
MAX_OPACITY_PERCENT = 100
# 桌面／工作列等外殼視窗不列出來，釘它們沒有意義
# Shell windows - desktop, taskbar - are not worth listing or pinning.
_SKIP_CLASSES = {"WorkerW", "Progman", "Shell_TrayWnd", "Button"}
_MIN_WIDTH = 120
_MIN_HEIGHT = 80

_HWND_TOPMOST = -1
_HWND_NOTOPMOST = -2
_SWP_NOMOVE = 0x0002
_SWP_NOSIZE = 0x0001
_SWP_NOACTIVATE = 0x0010
_GWL_EXSTYLE = -20
_WS_EX_LAYERED = 0x00080000
_LWA_ALPHA = 0x00000002


def available() -> bool:
    """這個平台能不能操作別的視窗。"""
    return sys.platform == "win32"


def clamp_opacity(percent) -> int:
    """
    透明度百分比夾在 20~100：低於 20 的視窗幾乎看不見，使用者會找不回來。
    Clamp the opacity to 20..100 - below that a window is effectively invisible
    and the user cannot find it again.
    """
    try:
        return max(MIN_OPACITY_PERCENT, min(MAX_OPACITY_PERCENT, int(percent)))
    except (TypeError, ValueError):
        return MAX_OPACITY_PERCENT


def alpha_from_percent(percent) -> int:
    """百分比 -> Win32 需要的 0~255 alpha。"""
    return int(round(clamp_opacity(percent) / 100.0 * 255))


def list_windows() -> List[Tuple[int, str]]:
    """
    列出可以釘選的視窗 [(handle, 標題)]；非 Windows 或失敗時回傳空清單。
    Pinnable windows as (handle, title); [] when unavailable.
    """
    if not available():
        return []
    try:
        return _list_windows_windows()
    except Exception as error:  # pragma: no cover - Win32 boundary
        front_engine_logger.warning(f"[WindowPin] list failed: {error!r}")
        return []


def _list_windows_windows() -> List[Tuple[int, str]]:  # pragma: no cover - Win32 boundary
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    windows: List[Tuple[int, str]] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    # EnumWindows 的回呼一定要回傳 True 才會繼續列舉；回 False 會中途停下。
    # 所以「永遠回傳同一個值」在這裡是規格要求，不是漏寫。
    # An EnumWindows callback must return True to keep enumerating; False
    # stops it early. Always returning the same value is the contract
    # here, not an oversight.
    def _collect(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return True
        if rect.right - rect.left < _MIN_WIDTH or rect.bottom - rect.top < _MIN_HEIGHT:
            return True
        class_buffer = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(hwnd, class_buffer, 64)
        if class_buffer.value in _SKIP_CLASSES:
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        title_buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title_buffer, length + 1)
        if title_buffer.value.strip():
            windows.append((int(hwnd), title_buffer.value))
        return True

    user32.EnumWindows(_collect, 0)
    return windows


def set_always_on_top(handle: int, on_top: bool) -> bool:
    """把某個視窗設成（或取消）永遠在最上層；成功回傳 True。"""
    if not available() or not handle:
        return False
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        # hWndInsertAfter 是 HWND（64 位元指標）。不宣告 argtypes 的話，
        # HWND_TOPMOST 的 -1 會被當成 32 位元整數截斷，呼叫就會失敗。
        # hWndInsertAfter is an HWND - a 64-bit pointer. Without argtypes the
        # -1 of HWND_TOPMOST is truncated to 32 bits and the call fails.
        user32.SetWindowPos.argtypes = [
            wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
            ctypes.c_int, ctypes.c_int, ctypes.c_uint,
        ]
        user32.SetWindowPos.restype = wintypes.BOOL
        inserted = _HWND_TOPMOST if on_top else _HWND_NOTOPMOST
        result = user32.SetWindowPos(
            wintypes.HWND(int(handle)), wintypes.HWND(inserted), 0, 0, 0, 0,
            _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOACTIVATE)
        front_engine_logger.info(f"[WindowPin] pin {handle} on_top={on_top} ok={bool(result)}")
        return bool(result)
    except Exception as error:  # pragma: no cover - Win32 boundary
        front_engine_logger.warning(f"[WindowPin] pin failed: {error!r}")
        return False


def set_opacity(handle: int, percent) -> bool:
    """
    調整某個視窗的透明度（20~100%）。100% 時仍保留分層旗標，方便再調回去。
    Set a window's opacity (20..100%). The layered flag stays on at 100% so it
    can be adjusted again without flicker.
    """
    if not available() or not handle:
        return False
    try:
        import ctypes

        user32 = ctypes.windll.user32
        style = user32.GetWindowLongW(int(handle), _GWL_EXSTYLE)
        user32.SetWindowLongW(int(handle), _GWL_EXSTYLE, style | _WS_EX_LAYERED)
        result = user32.SetLayeredWindowAttributes(
            int(handle), 0, alpha_from_percent(percent), _LWA_ALPHA)
        front_engine_logger.info(
            f"[WindowPin] opacity {handle} -> {clamp_opacity(percent)}% ok={bool(result)}")
        return bool(result)
    except Exception as error:  # pragma: no cover - Win32 boundary
        front_engine_logger.warning(f"[WindowPin] opacity failed: {error!r}")
        return False


def window_title(handle: int) -> Optional[str]:
    """某個 handle 目前的標題；找不到回傳 None。"""
    for known_handle, title in list_windows():
        if known_handle == int(handle):
            return title
    return None
