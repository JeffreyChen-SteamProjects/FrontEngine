"""
把視窗搬到下一個螢幕。

多螢幕的人每天都在做這件事，而 Windows 內建的 Win+Shift+方向鍵只會整個貼過去，
不保留視窗原本的大小比例。這裡搬的是「相對位置與相對大小」：視窗在來源螢幕的
右半邊佔三分之一，到了目標螢幕還是在右半邊佔三分之一，即使兩台螢幕解析度不同。

幾何運算全部是純函式（螢幕清單以 (x, y, w, h) 傳入），所以多螢幕的行為不必真的
接兩台螢幕就驗得了；實際的視窗操作沿用 window_layout 既有的 Win32 呼叫。

**座標空間**：螢幕矩形一律取 Win32 的實體像素，不能用 Qt 的邏輯像素——理由見
`win32_screen_rects()`。這是在雙螢幕（100% + 125%）實機上抓到的，純邏輯測試
看不出來，因為兩種座標在單一縮放比例下剛好相同。

Move a window to the next monitor.

Anyone with two screens does this daily, and Windows' own Win+Shift+Arrow snaps
the window across without keeping its proportions. This moves the *relative*
position and size: a window filling a third of the right half stays a third of
the right half on the other screen, even at a different resolution.

The geometry is pure (screens come in as (x, y, w, h) tuples), so multi-monitor
behaviour is testable without a second monitor; the actual window move reuses
window_layout's existing Win32 calls.
"""
from __future__ import annotations

import sys
from typing import List, Optional, Sequence, Tuple

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.window_pin.window_layout import MIN_SIZE, move_window, window_geometry

Rect = Tuple[int, int, int, int]


def overlap_area(first: Rect, second: Rect) -> int:
    """兩個矩形重疊的面積；沒有重疊回傳 0。"""
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[0] + first[2], second[0] + second[2])
    bottom = min(first[1] + first[3], second[1] + second[3])
    if right <= left or bottom <= top:
        return 0
    return (right - left) * (bottom - top)


def screen_index_for(rect: Rect, screens: Sequence[Rect]) -> Optional[int]:
    """
    視窗目前主要落在哪一個螢幕上（重疊面積最大的那個）。用面積而不是左上角
    座標：跨螢幕擺放的視窗，左上角可能還在上一台螢幕，但人看到的主體在另一台。
    Which screen the window mostly sits on, by overlap area rather than by its
    top-left corner: a window straddling two screens can have its corner on one
    while what the user sees is on the other.
    """
    best_index, best_area = None, 0
    for index, screen in enumerate(screens or ()):
        area = overlap_area(rect, screen)
        if area > best_area:
            best_index, best_area = index, area
    return best_index


def next_index(current: Optional[int], count: int, step: int = 1) -> Optional[int]:
    """下一個螢幕的索引（循環）。只有一個螢幕或算不出來時回傳 None。"""
    if count <= 1 or current is None:
        return None
    return (int(current) + int(step)) % int(count)


def mapped_rect(rect: Rect, source: Rect, target: Rect) -> Rect:
    """
    把視窗從來源螢幕等比例對應到目標螢幕，並保證仍落在目標螢幕範圍內。
    Map the window proportionally from one screen to the other, keeping it
    inside the target.
    """
    source_width = max(1, source[2])
    source_height = max(1, source[3])
    x_share = (rect[0] - source[0]) / source_width
    y_share = (rect[1] - source[1]) / source_height
    width_share = min(1.0, max(0.0, rect[2] / source_width))
    height_share = min(1.0, max(0.0, rect[3] / source_height))

    width = max(MIN_SIZE, min(target[2], round(width_share * target[2])))
    height = max(MIN_SIZE, min(target[3], round(height_share * target[3])))
    x = target[0] + round(x_share * target[2])
    y = target[1] + round(y_share * target[3])
    # 夾回目標螢幕內，否則從大螢幕搬到小螢幕時視窗會有一半掉在畫面外
    # Clamp into the target, or moving from a large screen to a small one
    # leaves half the window off the edge.
    x = max(target[0], min(x, target[0] + target[2] - width))
    y = max(target[1], min(y, target[1] + target[3] - height))
    return (int(x), int(y), int(width), int(height))


def clamp_into(rect: Rect, screen: Rect) -> Rect:
    """
    把矩形挪回螢幕內（只動位置，不改大小）。比螢幕還大的視窗貼齊左上角，
    因為那至少讓標題列和關閉鈕看得到——置中的話兩邊都在畫面外。
    Nudge a rectangle back inside a screen, moving but never resizing it. A
    window larger than the screen goes to the top-left, where its title bar and
    close button are at least reachable; centred, both edges would be off.
    """
    x, y, width, height = rect
    x = min(x, screen[0] + screen[2] - width)
    y = min(y, screen[1] + screen[3] - height)
    x = max(screen[0], x)
    y = max(screen[1], y)
    return (int(x), int(y), int(width), int(height))


def plan_move(rect: Rect, screens: Sequence[Rect], step: int = 1) -> Optional[Rect]:
    """
    算出視窗搬到下一個螢幕之後該有的矩形；只有一個螢幕、或判斷不出目前在哪一台
    時回傳 None（不動比亂搬好）。
    The rectangle the window should have on the next screen, or None with a
    single screen or when the current one cannot be told - leaving it alone
    beats moving it somewhere arbitrary.
    """
    current = screen_index_for(rect, screens)
    target = next_index(current, len(screens or ()), step)
    if target is None:
        return None
    return mapped_rect(rect, screens[current], screens[target])


def available() -> bool:
    """這個平台能不能搬別的程式的視窗。"""
    return sys.platform == "win32"


def foreground_window() -> Optional[int]:
    """目前前景視窗的 handle；取不到或非 Windows 回傳 None。"""
    if not available():
        return None
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        user32.GetForegroundWindow.restype = wintypes.HWND
        handle = user32.GetForegroundWindow()
        return int(handle) if handle else None
    except Exception as error:  # pragma: no cover - Win32 boundary
        front_engine_logger.warning(f"[MonitorMove] foreground failed: {error!r}")
        return None


def win32_screen_rects() -> List[Rect]:
    """
    Win32 的工作區，單位是**實體像素**（`EnumDisplayMonitors` + `GetMonitorInfoW`
    的 rcWork）。

    這裡不能用 Qt 的 `QScreen.availableGeometry()`：Qt 給的是**邏輯像素**，而
    `GetWindowRect` / `SetWindowPos` 用的是實體像素。兩台螢幕縮放比例不同時
    差距是實打實的——實測一台 100%、一台 125% 的機器上，Qt 說第二台是
    1536x816，Win32 說是 1920x1020。拿 Qt 的數字去算 SetWindowPos，視窗會照著
    一個小了四分之一的螢幕擺放，位置和大小都不對。

    The Win32 work areas in **physical pixels** (rcWork from EnumDisplayMonitors
    + GetMonitorInfoW).

    Qt's `QScreen.availableGeometry()` cannot be used here: Qt reports **logical**
    pixels while GetWindowRect and SetWindowPos speak physical ones. With two
    screens at different scaling the gap is real - measured on a 100% + 125%
    machine, Qt calls the second screen 1536x816 and Win32 calls it 1920x1020.
    Sizing a SetWindowPos call from Qt's numbers lays the window out against a
    screen a quarter smaller than the real one.
    """
    if not available():
        return []
    try:
        import ctypes
        from ctypes import wintypes

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT),
                ("dwFlags", wintypes.DWORD),
            ]

        monitor_enum_proc = ctypes.WINFUNCTYPE(
            wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
            ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        rects: List[Rect] = []

        def collect(monitor, _hdc, _rect, _param):
            info = MONITORINFO()
            info.cbSize = ctypes.sizeof(MONITORINFO)
            if user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                work = info.rcWork
                rects.append((work.left, work.top,
                              work.right - work.left, work.bottom - work.top))
            return True

        user32.EnumDisplayMonitors(None, None, monitor_enum_proc(collect), 0)
        return rects
    except Exception as error:  # pragma: no cover - Win32 boundary
        front_engine_logger.warning(f"[MonitorMove] monitor enumeration failed: {error!r}")
        return []


def qt_screen_rects(screens) -> List[Rect]:
    """QScreen 物件 -> (x, y, 寬, 高)。邏輯像素，測試與非 Windows 平台用。"""
    rects = []
    for screen in screens or ():
        area = screen.availableGeometry()
        rects.append((area.x(), area.y(), area.width(), area.height()))
    return rects


def screen_rects(screens=None) -> List[Rect]:
    """
    目前每個螢幕的 (x, y, 寬, 高)，用可用區域而不是完整 geometry，搬過去的視窗
    才不會被工作列蓋住標題列。Windows 上走 Win32（實體像素，和實際搬移視窗的
    呼叫同一個座標空間），其餘平台與明確傳入 screens 時走 Qt。
    Each screen as (x, y, w, h) from the work area, so a moved window does not
    land with its title bar under the taskbar. On Windows this comes from Win32
    in physical pixels - the same space as the calls that actually move the
    window - and from Qt elsewhere or when screens are passed in explicitly.
    """
    if screens is not None:
        return qt_screen_rects(screens)
    if available():
        rects = win32_screen_rects()
        if rects:
            return rects
    from PySide6.QtGui import QGuiApplication

    return qt_screen_rects(QGuiApplication.screens())


def move_to_next_monitor(step: int = 1, screens=None, handle=None,
                         geometry_reader=None, mover=None) -> bool:
    """
    把前景視窗搬到下一個螢幕；成功回傳 True。每一個對外界的呼叫都可注入，
    所以整條流程在沒有第二台螢幕、也沒有 Win32 的機器上測得完整。
    Move the foreground window to the next screen, True when it moved. Every
    call to the outside world is injectable, so the whole flow is testable
    without a second monitor or Win32.
    """
    target_handle = handle if handle is not None else foreground_window()
    if not target_handle:
        return False
    read = geometry_reader or window_geometry
    rect = read(target_handle)
    if rect is None:
        return False
    rects = screen_rects(screens)
    plan = plan_move(tuple(rect), rects, step)
    if plan is None:
        front_engine_logger.info("[MonitorMove] nowhere to move to")
        return False
    move = mover or move_window
    moved = move(target_handle, *plan)
    front_engine_logger.info(f"[MonitorMove] {rect} -> {plan} ok={moved}")
    if moved:
        _settle_inside_screen(target_handle, plan, rects, read, move)
    return bool(moved)


def _settle_inside_screen(handle, plan: Rect, rects: Sequence[Rect], read, move) -> None:
    """
    搬完之後再確認一次視窗真的整個在目標螢幕裡，不在就把它挪回去（不改大小）。

    為什麼需要這一步：跨越 DPI 不同的螢幕時，Windows 會在 SetWindowPos 之後
    自己送 WM_DPICHANGED 把視窗依比例放大（實測 100% -> 125% 的螢幕，寬度會被
    乘上 1.25）。那個放大是對的——視覺大小才會一致——但它發生在我們算好位置
    之後，所以原本剛好貼齊右緣的視窗會被推出畫面。這裡不去對抗 OS 的縮放，
    只把落地後的結果夾回螢幕內。
    Confirm the window really ended up inside the target screen, and nudge it
    back if not, without resizing.

    Why this exists: crossing a DPI boundary, Windows follows our SetWindowPos
    with its own WM_DPICHANGED and scales the window up (measured: x1.25 going
    from a 100% to a 125% screen). That scaling is right - it keeps the apparent
    size - but it happens after our arithmetic, so a window flush against the
    right edge gets pushed off it. Rather than fight the OS, this clamps the
    result back in.
    """
    target = screen_index_for(plan, rects)
    if target is None:
        return
    try:
        landed = read(handle)
    except Exception:  # pragma: no cover - defensive around an injected reader
        return
    if landed is None:
        return
    settled = clamp_into(tuple(landed), rects[target])
    if settled[:2] != tuple(landed)[:2]:
        front_engine_logger.info(f"[MonitorMove] settling {tuple(landed)} -> {settled}")
        move(handle, *settled)
