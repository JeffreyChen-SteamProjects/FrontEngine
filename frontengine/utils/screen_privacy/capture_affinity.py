"""
把視窗排除在螢幕擷取之外：分享畫面時，自己看得到覆蓋層，對方看不到。

用的是 Win32 的 `SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)`。這是作業系統
層級的旗標——會議軟體、錄影軟體、螢幕擷取 API 拿到的畫面裡那塊會是空的，
而本機螢幕上照常顯示。僅 Windows 10 2004 以後有效，其他平台一律回報做不到。

**這是「隱私」不是「保全」**：它擋的是正常的擷取管道，不是防止有心人用其他
方式取得畫面，也不會讓視窗對使用者自己隱形。

Keep a window out of screen captures: you still see your overlays while the
people you are sharing with do not.

This is Win32's `SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)` - an
OS-level flag, so conferencing apps, recorders and capture APIs all receive
blank pixels there while the local display is unchanged. Windows 10 2004 and
later; everywhere else it reports that it cannot be done.

**This is privacy, not security**: it defeats the ordinary capture path, not a
determined attacker, and it never hides the window from the person at the desk.
"""
from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Iterable, Optional

from frontengine.utils.logging.loggin_instance import front_engine_logger

if TYPE_CHECKING:  # 只為了型別標註，執行時不需要把 Qt 拉進這支純 ctypes 工具
    from PySide6.QtWidgets import QWidget

# WDA_NONE：正常擷取；WDA_EXCLUDEFROMCAPTURE：擷取時整片留白
# WDA_NONE captures normally; WDA_EXCLUDEFROMCAPTURE comes out blank.
WDA_NONE = 0x00000000
WDA_EXCLUDEFROMCAPTURE = 0x00000011


def available() -> bool:
    """這個平台能不能控制擷取可見性。"""
    return sys.platform == "win32"


def _user32():
    """拿到宣告好 argtypes 的 user32；非 Windows 回傳 None。"""
    if not available():
        return None
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
    user32.SetWindowDisplayAffinity.restype = wintypes.BOOL
    user32.GetWindowDisplayAffinity.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowDisplayAffinity.restype = wintypes.BOOL
    return user32


def set_excluded_from_capture(handle: int, excluded: bool) -> bool:
    """
    設定某個視窗要不要被排除在擷取之外；成功回傳 True。
    Set whether a window is excluded from capture; True when it took effect.
    """
    user32 = _user32()
    if user32 is None or not handle:
        return False
    try:
        from ctypes import wintypes

        affinity = WDA_EXCLUDEFROMCAPTURE if excluded else WDA_NONE
        result = user32.SetWindowDisplayAffinity(wintypes.HWND(int(handle)), affinity)
        front_engine_logger.debug(
            f"[CaptureAffinity] {handle} excluded={excluded} ok={bool(result)}")
        return bool(result)
    except Exception as error:  # pragma: no cover - Win32 boundary
        front_engine_logger.warning(f"[CaptureAffinity] failed: {error!r}")
        return False


def is_excluded_from_capture(handle: int) -> Optional[bool]:
    """某個視窗目前是不是被排除在擷取之外；問不到回傳 None。"""
    user32 = _user32()
    if user32 is None or not handle:
        return None
    try:
        import ctypes
        from ctypes import wintypes

        affinity = wintypes.DWORD()
        if not user32.GetWindowDisplayAffinity(wintypes.HWND(int(handle)),
                                               ctypes.byref(affinity)):
            return None
        return affinity.value == WDA_EXCLUDEFROMCAPTURE
    except Exception as error:  # pragma: no cover - Win32 boundary
        front_engine_logger.debug(f"[CaptureAffinity] read failed: {error!r}")
        return None


def apply_to_widget(widget: Optional[QWidget], excluded: bool) -> bool:
    """
    對一個 Qt widget 套用擷取可見性。視窗還沒建立原生 handle 時回傳 False，
    呼叫端可以等 show() 之後再試一次。
    Apply capture visibility to a Qt widget. False when it has no native handle
    yet, so the caller can try again after show().
    """
    if widget is None:
        return False
    try:
        handle = int(widget.winId())
    except (RuntimeError, ValueError):  # pragma: no cover - widget torn down
        return False
    return set_excluded_from_capture(handle, excluded)


def apply_to_widgets(widgets: Optional[Iterable[QWidget]], excluded: bool) -> int:
    """對一批 widget 套用，回傳成功的數量。"""
    applied = 0
    for widget in tuple(widgets or ()):
        try:
            if apply_to_widget(widget, excluded):
                applied += 1
        except RuntimeError:  # pragma: no cover - widget closed mid-loop
            continue
    return applied
