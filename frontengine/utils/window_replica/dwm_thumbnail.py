"""
用 DWM 縮圖做出另一個視窗的即時複本。

這和「釘選視窗」是兩件事：釘選是把**原視窗**搬到最上層，原本在哪就不在哪了；
複本是另外開一個小視窗顯示它的即時畫面，原視窗留在原地不動。想邊工作邊看影片、
或盯著背景的編譯進度，要的是後者。

畫面由 DWM 直接合成，不需要抓圖也不需要輪詢，所以更新是即時的而且幾乎不耗 CPU。
Windows 專屬：其他平台一律回報「做不到」，不假裝成功。

A live replica of another window, via DWM thumbnails.

This is not window pinning. Pinning moves the *real* window to the top, so it is
no longer where it was; a replica is a second small window showing its live
picture while the original stays put. Watching a video or a build log while
working is the second thing.

DWM composites the picture itself - no screen grabbing, no polling - so it is
live and costs almost nothing. Windows only: every other platform reports "not
possible" rather than pretending.
"""
from __future__ import annotations

import sys
from typing import Optional, Tuple

from frontengine.utils.logging.loggin_instance import front_engine_logger

# DWM_THUMBNAIL_PROPERTIES 的旗標 / Flags for DWM_THUMBNAIL_PROPERTIES
DWM_TNP_RECTDESTINATION = 0x00000001
DWM_TNP_RECTSOURCE = 0x00000002
DWM_TNP_OPACITY = 0x00000004
DWM_TNP_VISIBLE = 0x00000008
DWM_TNP_SOURCECLIENTAREAONLY = 0x00000010

MIN_REPLICA_SIZE = 80
DEFAULT_REPLICA_WIDTH = 480


def available() -> bool:
    """這個平台能不能做視窗複本。"""
    return sys.platform == "win32"


def fit_within(source: Tuple[int, int], bounds: Tuple[int, int]) -> Tuple[int, int]:
    """
    把來源尺寸等比縮到不超過 bounds，並保持長寬比。

    純算術，所以縮放這件事不必開一個真的視窗才能驗證。來源尺寸拿不到時會是 0，
    這裡直接回傳 bounds 而不是除以零。
    Scale the source into `bounds` keeping its aspect ratio. Pure arithmetic, so
    the scaling can be checked without opening a window. A source size can come
    back as 0, in which case this returns the bounds rather than dividing by it.
    """
    source_width, source_height = source
    max_width, max_height = bounds
    if source_width <= 0 or source_height <= 0:
        return max(MIN_REPLICA_SIZE, max_width), max(MIN_REPLICA_SIZE, max_height)
    scale = min(max_width / source_width, max_height / source_height)
    width = max(MIN_REPLICA_SIZE, int(source_width * scale))
    height = max(MIN_REPLICA_SIZE, int(source_height * scale))
    return width, height


class DwmThumbnail:
    """
    一個註冊好的 DWM 縮圖。register() 開始、update() 調整、unregister() 收掉。

    縮圖是系統資源，忘了 unregister 的話 DWM 會一直替一個已經看不到的目的地合成
    畫面。釋放一律由呼叫端明確做，**沒有** __del__ 兜底：直譯器關閉時的解構順序
    不保證，那時 ctypes 載入的 dwmapi 可能已經不在，靠它反而是靠一個不會發生的
    保險。實際的三條路徑是覆蓋層的 closeEvent、對話框的 close_all()、以及主程式
    關閉時的收尾。

    A registered DWM thumbnail. It is a system resource: forgetting to
    unregister leaves DWM compositing for a destination nobody can see.

    Releasing is always explicit, with **no** __del__ fallback: destruction order
    at interpreter shutdown is not guaranteed and the ctypes-loaded dwmapi may
    already be gone, so relying on it means relying on something that may never
    run. The three real paths are the overlay's closeEvent, the dialog's
    close_all(), and the application's own shutdown.
    """

    def __init__(self) -> None:
        self._handle: Optional[int] = None
        self._dwmapi = None

    @property
    def registered(self) -> bool:
        return self._handle is not None

    def register(self, destination: int, source: int) -> bool:
        """把 source 視窗的畫面接到 destination 視窗上。"""
        if not available():
            return False
        self.unregister()
        try:
            import ctypes
            from ctypes import wintypes

            dwmapi = ctypes.windll.dwmapi
            handle = wintypes.HANDLE()
            result = dwmapi.DwmRegisterThumbnail(
                wintypes.HWND(destination), wintypes.HWND(source), ctypes.byref(handle))
            if result != 0 or not handle.value:
                front_engine_logger.warning(
                    f"[DwmThumbnail] register failed | hresult={result}")
                return False
            self._dwmapi = dwmapi
            self._handle = handle.value
            return True
        except Exception as error:  # pragma: no cover - Win32 boundary
            front_engine_logger.warning(f"[DwmThumbnail] register error: {error!r}")
            return False

    def source_size(self) -> Tuple[int, int]:
        """來源視窗的原始尺寸；問不到就回 (0, 0)。"""
        if self._handle is None or self._dwmapi is None:
            return (0, 0)
        try:
            import ctypes
            from ctypes import wintypes

            class SIZE(ctypes.Structure):
                _fields_ = [("cx", wintypes.LONG), ("cy", wintypes.LONG)]

            size = SIZE()
            if self._dwmapi.DwmQueryThumbnailSourceSize(
                    wintypes.HANDLE(self._handle), ctypes.byref(size)) != 0:
                return (0, 0)
            return (int(size.cx), int(size.cy))
        except Exception as error:  # pragma: no cover - Win32 boundary
            front_engine_logger.warning(f"[DwmThumbnail] source size error: {error!r}")
            return (0, 0)

    def update(self, width: int, height: int, opacity: int = 255,
               client_area_only: bool = True) -> bool:
        """把縮圖鋪滿目的地視窗的這個大小。"""
        if self._handle is None or self._dwmapi is None:
            return False
        try:
            import ctypes
            from ctypes import wintypes

            class RECT(ctypes.Structure):
                _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                            ("right", wintypes.LONG), ("bottom", wintypes.LONG)]

            class DWM_THUMBNAIL_PROPERTIES(ctypes.Structure):
                _fields_ = [
                    ("dwFlags", wintypes.DWORD),
                    ("rcDestination", RECT),
                    ("rcSource", RECT),
                    ("opacity", ctypes.c_ubyte),
                    ("fVisible", wintypes.BOOL),
                    ("fSourceClientAreaOnly", wintypes.BOOL),
                ]

            properties = DWM_THUMBNAIL_PROPERTIES()
            properties.dwFlags = (DWM_TNP_RECTDESTINATION | DWM_TNP_OPACITY
                                  | DWM_TNP_VISIBLE | DWM_TNP_SOURCECLIENTAREAONLY)
            properties.rcDestination = RECT(0, 0, max(1, int(width)), max(1, int(height)))
            properties.opacity = max(0, min(255, int(opacity)))
            properties.fVisible = True
            # 只取客戶區：不然複本裡會有一圈原視窗的標題列與邊框，看起來像截圖失誤。
            # Client area only: otherwise the replica carries the source's title
            # bar and border, which reads as a botched screenshot.
            properties.fSourceClientAreaOnly = bool(client_area_only)
            result = self._dwmapi.DwmUpdateThumbnailProperties(
                wintypes.HANDLE(self._handle), ctypes.byref(properties))
            return result == 0
        except Exception as error:  # pragma: no cover - Win32 boundary
            front_engine_logger.warning(f"[DwmThumbnail] update error: {error!r}")
            return False

    def unregister(self) -> None:
        """收掉縮圖。重複呼叫是安全的。"""
        if self._handle is None or self._dwmapi is None:
            self._handle = None
            return
        try:
            from ctypes import wintypes

            self._dwmapi.DwmUnregisterThumbnail(wintypes.HANDLE(self._handle))
        except Exception as error:  # pragma: no cover - Win32 boundary
            front_engine_logger.warning(f"[DwmThumbnail] unregister error: {error!r}")
        finally:
            self._handle = None
