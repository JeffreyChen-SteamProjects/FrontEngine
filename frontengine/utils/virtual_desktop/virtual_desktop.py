"""
虛擬桌面感知：讓覆蓋層只留在開啟它的那個虛擬桌面上。

用的是**有文件的** `IVirtualDesktopManager`（Shell COM 介面），只呼叫
`IsWindowOnCurrentVirtualDesktop` 與 `GetWindowDesktopId`。市面上做「每個虛擬桌面
不同桌布」的專案多半得用未公開的 COM 介面，那些介面**每個 Windows 版本都會變**，
壞掉的時候還是無聲的；這裡刻意只用公開的那一半，換到的是「桌面切走就隱藏」，
少了「每個桌面不同內容」，但不會在某次 Windows 更新之後莫名其妙失效。

**無頭測試碰不到真正的桌面切換**：CI 上沒有第二個虛擬桌面。因此探測函式是可注入
的，邏輯層（誰該隱藏、誰該還原）測得完整，而真正的 COM 呼叫只有在 Windows 上
執行時才會走到。

實機量過的行為（Windows 11，2026-08）：
  * 自己桌面上的視窗 -> True；建一個新的虛擬桌面切過去之後 -> False，切回來
    又是 True。整條路（隱藏、還原）都成立。
  * **不認識的 handle 會回傳 S_OK 加 True**，不是 False 也不是錯誤。這是安全的
    方向：已經關掉的覆蓋層不會被誤判成「在別的桌面」而被藏起來。
    （`GetWindowDesktopId` 相對嚴謹，同樣的 handle 會回 `TYPE_E_ELEMENTNOTFOUND`。）

Virtual desktop awareness: keep an overlay on the desktop it was opened on.

This uses the **documented** `IVirtualDesktopManager` shell COM interface and
only calls `IsWindowOnCurrentVirtualDesktop` and `GetWindowDesktopId`. Projects
that give each virtual desktop its own wallpaper generally reach for the
undocumented interfaces, which change with **every Windows release** and fail
silently when they do. Sticking to the public half buys "hide when the desktop
is switched away" instead of "different content per desktop", and it will not
quietly stop working after an update.

**A real desktop switch cannot be exercised headlessly**: CI has no second
virtual desktop and no way to switch to one. So the probe is injectable, the
logic - who to hide, who to restore - is fully tested, and the COM call itself
is only reached when actually running on Windows.
"""
from __future__ import annotations

import sys
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from frontengine.utils.logging.loggin_instance import front_engine_logger

# Shell 的虛擬桌面管理員 / The shell's virtual desktop manager.
CLSID_VIRTUAL_DESKTOP_MANAGER = "{AA509086-5CA9-4C25-8F95-589D3C07B48A}"
IID_VIRTUAL_DESKTOP_MANAGER = "{A5CD92FF-29BE-454C-8D04-D82879FB3F1B}"
# IUnknown 佔了 vtable 前三格，之後才是這個介面自己的方法。
# IUnknown takes the first three vtable slots; the interface's own follow.
_VTBL_IS_ON_CURRENT_DESKTOP = 3
_VTBL_GET_WINDOW_DESKTOP_ID = 4
_CLSCTX_INPROC_SERVER = 0x1
DEFAULT_INTERVAL_MS = 1000

_manager: Optional[Any] = None
_manager_failed = False


def available() -> bool:
    """這個平台有沒有虛擬桌面管理員。"""
    return sys.platform == "win32"


def _guid_type():
    import ctypes

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", ctypes.c_ulong),
            ("Data2", ctypes.c_ushort),
            ("Data3", ctypes.c_ushort),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    return GUID


def _create_manager():
    """
    建立 IVirtualDesktopManager；失敗擲出 OSError。COM 初始化用
    COINIT_APARTMENTTHREADED，而且已經初始化過（S_FALSE / RPC_E_CHANGED_MODE）
    不算錯誤——這支程式的其他部分也會初始化 COM。
    Create the manager, raising OSError on failure. COM is initialised
    apartment-threaded, and an already-initialised apartment (S_FALSE or
    RPC_E_CHANGED_MODE) is not an error: other parts of this application
    initialise COM too.
    """
    if not available():
        raise OSError("virtual desktops are Windows only")
    import ctypes

    ole32 = ctypes.windll.ole32  # type: ignore[attr-defined]
    ole32.CoInitializeEx(None, 0x2)
    guid_type = _guid_type()
    class_id, interface_id = guid_type(), guid_type()
    if ole32.CLSIDFromString(CLSID_VIRTUAL_DESKTOP_MANAGER, ctypes.byref(class_id)) != 0:
        raise OSError("bad virtual desktop manager CLSID")
    if ole32.IIDFromString(IID_VIRTUAL_DESKTOP_MANAGER, ctypes.byref(interface_id)) != 0:
        raise OSError("bad virtual desktop manager IID")
    pointer = ctypes.c_void_p()
    result = ole32.CoCreateInstance(
        ctypes.byref(class_id), None, _CLSCTX_INPROC_SERVER,
        ctypes.byref(interface_id), ctypes.byref(pointer))
    if result != 0 or not pointer:
        raise OSError(f"CoCreateInstance failed: 0x{result & 0xFFFFFFFF:08x}")
    return pointer


def _shared_manager():
    """快取的管理員；建不起來就記住失敗，不要每秒重試一次。"""
    global _manager, _manager_failed
    if _manager is not None or _manager_failed:
        return _manager
    try:
        _manager = _create_manager()
    except Exception as error:
        _manager_failed = True
        front_engine_logger.info(f"[virtual_desktop] unavailable: {error!r}")
    return _manager


def _call_is_on_current_desktop(handle: int) -> Optional[bool]:
    """真的呼叫 COM。任何失敗都回傳 None（＝不知道），不擲出例外。"""
    manager = _shared_manager()
    if manager is None:
        return None
    import ctypes

    try:
        vtable = ctypes.cast(manager, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
        prototype = ctypes.WINFUNCTYPE(
            ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int))
        method = prototype(vtable[_VTBL_IS_ON_CURRENT_DESKTOP])
        answer = ctypes.c_int(0)
        result = method(manager, ctypes.c_void_p(int(handle)), ctypes.byref(answer))
        if result != 0:
            return None
        return bool(answer.value)
    except Exception as error:  # pragma: no cover - COM boundary
        front_engine_logger.debug(f"[virtual_desktop] probe failed: {error!r}")
        return None


def is_window_on_current_desktop(handle, probe: Optional[Callable] = None) -> Optional[bool]:
    """
    這個視窗在不在目前的虛擬桌面上。回答不出來時回傳 None——**不是 False**：
    「不知道」和「不在」必須分得開，否則在沒有虛擬桌面 API 的機器上，
    每一個覆蓋層都會被判定成「不在這個桌面」而被藏起來。

    注意底層 API 對「不認識的 handle」是回傳 True 而不是錯誤（見模組說明），
    所以這裡的 None 實務上來自沒有 handle、非 Windows、或 COM 建不起來。
    Whether the window is on the current virtual desktop, or None when it
    cannot be told - **not False**. "Unknown" and "no" have to stay distinct,
    or on a machine without the API every overlay reads as "not here" and gets
    hidden.
    """
    if not handle:
        return None
    caller = probe or _call_is_on_current_desktop
    try:
        answer = caller(int(handle))
    except Exception as error:  # pragma: no cover - defensive around an injected probe
        front_engine_logger.debug(f"[virtual_desktop] probe raised: {error!r}")
        return None
    return None if answer is None else bool(answer)


def widget_handle(widget) -> Optional[int]:
    """widget 的原生視窗 handle；還沒建立或已被銷毀時回傳 None。"""
    if widget is None:
        return None
    try:
        handle = int(widget.winId())
    except (RuntimeError, ValueError, AttributeError):
        return None
    return handle or None


class DesktopVisibility:
    """
    決定「誰該被藏、誰該被放回來」的純邏輯。記住自己藏過哪些覆蓋層，
    只還原自己藏的那些——使用者手動隱藏的不該被這個服務擅自放回來。
    The pure decision of who to hide and who to bring back. It remembers what
    it hid and restores only that: an overlay the user hid by hand is not this
    service's to re-show.
    """

    def __init__(self) -> None:
        self._hidden: List[int] = []

    def hidden_count(self) -> int:
        return len(self._hidden)

    def was_hidden(self, handle) -> bool:
        """這個 handle 是不是被本服務藏起來的。"""
        return handle in self._hidden

    def forget(self) -> None:
        """忘掉紀錄（服務停止時呼叫），下次重新判斷。"""
        self._hidden = []

    def decide(self, widgets, probe: Optional[Callable] = None) -> Dict[str, list]:
        """
        回傳 {"hide": [...], "show": [...]}。判斷不出來的一律不動——見
        `is_window_on_current_desktop` 對 None 的說明。
        Returns what to hide and what to bring back. Anything undecidable is
        left alone; see the note on None in is_window_on_current_desktop.
        """
        to_hide, to_show = [], []
        alive = []
        for widget in tuple(widgets or ()):
            handle = widget_handle(widget)
            if handle is None:
                continue
            alive.append(handle)
            on_current = is_window_on_current_desktop(handle, probe)
            if on_current is None:
                continue
            if not on_current:
                if handle not in self._hidden:
                    self._hidden.append(handle)
                    to_hide.append(widget)
            elif handle in self._hidden:
                self._hidden.remove(handle)
                to_show.append(widget)
        # 已經關掉的覆蓋層要從紀錄裡剔除，否則 handle 被作業系統回收再配給
        # 別的視窗時，會把不相干的東西當成「我藏的」放回來。
        # Drop closed overlays: a recycled handle would otherwise let this
        # service "restore" a window it never hid.
        self._hidden = [handle for handle in self._hidden if handle in alive]
        return {"hide": to_hide, "show": to_show}


class VirtualDesktopService(QObject):
    """
    定時檢查覆蓋層是否還在目前的虛擬桌面上，切走就隱藏、切回來就還原。
    覆蓋層來源與探測函式都可注入。
    Poll whether the overlays are still on the current virtual desktop, hiding
    and restoring as it changes. Both the overlay source and the probe are
    injectable.
    """

    changed = Signal(int, int)  # (hidden count, restored count)

    def __init__(self, widgets_provider: Optional[Callable] = None,
                 probe: Optional[Callable] = None,
                 interval_ms: int = DEFAULT_INTERVAL_MS,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._widgets_provider = widgets_provider or (lambda: [])
        self._probe = probe
        self._visibility = DesktopVisibility()
        self._timer = QTimer(self)
        self._timer.setInterval(max(200, int(interval_ms)))
        self._timer.timeout.connect(self.poll_once)

    def running(self) -> bool:
        return self._timer.isActive()

    def set_probe(self, probe: Optional[Callable]) -> None:
        """換掉探測函式（測試用；正式執行時是 None ＝ 走真正的 COM 呼叫）。"""
        self._probe = probe

    def start(self) -> None:
        if not self._timer.isActive():
            front_engine_logger.info("[VirtualDesktopService] start")
            self._timer.start()

    def stop(self) -> None:
        """
        停止並把自己藏起來的覆蓋層放回來。少了這一步，關掉這個功能之後
        那些覆蓋層就永遠留在隱藏狀態，而畫面上沒有任何線索說明為什麼。
        Stop, and bring back what it hid. Without this, switching the feature
        off leaves those overlays hidden for good with nothing on screen to
        explain why.
        """
        self._timer.stop()
        for widget in tuple(self._widgets_provider() or ()):
            handle = widget_handle(widget)
            if handle is not None and self._visibility.was_hidden(handle):
                try:
                    widget.show()
                except RuntimeError:  # pragma: no cover - closed mid-restore
                    continue
        self._visibility.forget()
        front_engine_logger.info("[VirtualDesktopService] stop")

    def poll_once(self) -> Dict[str, list]:
        try:
            widgets = self._widgets_provider() or []
        except Exception as error:  # pragma: no cover - defensive boundary
            front_engine_logger.warning(f"[VirtualDesktopService] source failed: {error!r}")
            return {"hide": [], "show": []}
        decision = self._visibility.decide(widgets, self._probe)
        for widget in decision["hide"]:
            try:
                widget.hide()
            except RuntimeError:  # pragma: no cover - closed mid-poll
                continue
        for widget in decision["show"]:
            try:
                widget.show()
            except RuntimeError:  # pragma: no cover - closed mid-poll
                continue
        if decision["hide"] or decision["show"]:
            self.changed.emit(len(decision["hide"]), len(decision["show"]))
        return decision
