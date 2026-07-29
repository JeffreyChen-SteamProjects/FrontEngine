"""
視窗版面：把目前每個視窗的位置記下來，之後一鍵擺回去。

配對是用視窗標題比對的——重開程式之後 handle 一定會變，但標題通常還在。
比對是「正規化後的標題相同」，找不到的視窗就跳過，不會亂搬別人的東西。
僅 Windows 有效（沿用 window_pin 的 Win32 呼叫）。

Window layouts: remember where every window sits now, and put them back later.

Windows are matched by title, because handles change when a program restarts
while its title usually does not. Matching is on the normalized title, and a
window that is not found is skipped rather than guessed at. Windows only.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.window_pin.window_pin import available, list_windows

_SWP_NOZORDER = 0x0004
_SWP_NOACTIVATE = 0x0010
MIN_SIZE = 40


def normalize_title(title: Any) -> str:
    """把視窗標題正規化成可比對的鍵（去頭尾空白、壓縮空白、轉小寫）。"""
    return " ".join(str(title or "").split()).lower()


def window_geometry(handle: int) -> Optional[Tuple[int, int, int, int]]:
    """某個視窗目前的 (x, y, 寬, 高)；取不到回傳 None。"""
    if not available() or not handle:
        return None
    try:
        import ctypes
        from ctypes import wintypes

        rect = wintypes.RECT()
        if not ctypes.windll.user32.GetWindowRect(int(handle), ctypes.byref(rect)):
            return None
        return (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)
    except Exception as error:  # pragma: no cover - Win32 boundary
        front_engine_logger.warning(f"[WindowLayout] geometry failed: {error!r}")
        return None


def move_window(handle: int, x: int, y: int, width: int, height: int) -> bool:
    """把視窗搬到指定位置與大小；成功回傳 True。"""
    if not available() or not handle:
        return False
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        # 和釘選一樣，hWndInsertAfter 是指標大小，一定要宣告 argtypes
        # As with pinning, hWndInsertAfter is pointer-sized: declare argtypes.
        user32.SetWindowPos.argtypes = [
            wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
            ctypes.c_int, ctypes.c_int, ctypes.c_uint,
        ]
        user32.SetWindowPos.restype = wintypes.BOOL
        return bool(user32.SetWindowPos(
            wintypes.HWND(int(handle)), wintypes.HWND(0),
            int(x), int(y), max(MIN_SIZE, int(width)), max(MIN_SIZE, int(height)),
            _SWP_NOZORDER | _SWP_NOACTIVATE))
    except Exception as error:  # pragma: no cover - Win32 boundary
        front_engine_logger.warning(f"[WindowLayout] move failed: {error!r}")
        return False


def capture_layout(lister=None, geometry_reader=None) -> List[Dict[str, Any]]:
    """
    記下目前每個視窗的標題與位置。列舉與讀取位置都可注入，方便測試。
    Record every window's title and place. Both the listing and the geometry
    read are injectable for tests.
    """
    windows = (lister or list_windows)() or []
    read = geometry_reader or window_geometry
    layout: List[Dict[str, Any]] = []
    for handle, title in windows:
        geometry = read(handle)
        if geometry is None:
            continue
        layout.append({
            "title": str(title),
            "x": int(geometry[0]), "y": int(geometry[1]),
            "width": int(geometry[2]), "height": int(geometry[3]),
        })
    return layout


def normalize_layout(layout: Any) -> List[Dict[str, Any]]:
    """整理儲存的版面資料，跳過缺欄位或壞掉的項目。"""
    if not isinstance(layout, (list, tuple)):
        return []
    cleaned: List[Dict[str, Any]] = []
    for entry in layout:
        if not isinstance(entry, dict) or not str(entry.get("title", "")).strip():
            continue
        try:
            cleaned.append({
                "title": str(entry["title"]),
                "x": int(entry.get("x", 0)), "y": int(entry.get("y", 0)),
                "width": max(MIN_SIZE, int(entry.get("width", MIN_SIZE))),
                "height": max(MIN_SIZE, int(entry.get("height", MIN_SIZE))),
            })
        except (TypeError, ValueError):
            continue
    return cleaned


def restore_layout(layout: Any, lister=None, mover=None) -> Tuple[int, int]:
    """
    把版面套回去，回傳 (搬動的視窗數, 找不到的視窗數)。標題對不上的就跳過。
    Apply a layout, returning (moved, missing). A title with no matching window
    on screen is skipped, never guessed at.
    """
    entries = normalize_layout(layout)
    if not entries:
        return (0, 0)
    windows = (lister or list_windows)() or []
    # 同名視窗很常見（兩個「文件」的檔案總管、兩份同檔名的文件）。用 dict 存
    # 單一 handle 的話後面的會蓋掉前面的，結果是同一個視窗被搬兩次、另一個
    # 完全沒動，回報卻說兩個都搬好了。每個標題存一串 handle，用掉一個就取走。
    # Windows sharing a title are common: two Explorer windows both called
    # "Documents", two copies of the same document. Keeping one handle per title
    # lets the later one overwrite the earlier, so one window gets moved twice,
    # another is never touched, and the report claims both were placed. Keep a
    # queue of handles per title and consume one per entry.
    by_title: Dict[str, List[int]] = {}
    for handle, title in windows:
        by_title.setdefault(normalize_title(title), []).append(handle)
    move = mover or move_window
    moved = missing = 0
    for entry in entries:
        handles = by_title.get(normalize_title(entry["title"]))
        if not handles:
            missing += 1
            continue
        handle = handles.pop(0)
        if move(handle, entry["x"], entry["y"], entry["width"], entry["height"]):
            moved += 1
    front_engine_logger.info(f"[WindowLayout] restored | moved={moved}, missing={missing}")
    return (moved, missing)
