"""
MIDI 控制器輸入：用旋鈕調不透明度、用按鍵切預設集。

走 Windows 內建的 winmm（和 WASAPI 一樣用 ctypes 直接呼叫），所以不需要新增
任何相依套件。訊息解析是純函式，沒有 MIDI 裝置也測得到。

MIDI controller input: turn a knob to change opacity, press a pad to switch
preset.

It goes through Windows' built-in winmm with ctypes, the same way the WASAPI
code does, so it needs no new dependency. Message parsing is pure, so it is
testable without a MIDI device present.
"""
from __future__ import annotations

import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, Signal

from frontengine.utils.logging.loggin_instance import front_engine_logger

# MIDI 狀態位元組的高四位：訊息種類
# The high nibble of a status byte is the message kind.
NOTE_OFF = 0x80
NOTE_ON = 0x90
CONTROL_CHANGE = 0xB0

KIND_NOTE = "note"
KIND_CONTROL = "control"
_MIM_DATA = 0x3C3
_CALLBACK_FUNCTION = 0x00030000


def available() -> bool:
    """這個平台能不能收 MIDI（目前只有 Windows 的 winmm）。"""
    return sys.platform == "win32"


def parse_message(value: Any) -> Optional[Dict[str, Any]]:
    """
    把 winmm 傳來的 32 位元訊息拆成看得懂的欄位。

    低位到高位依序是狀態、資料1、資料2。力度為 0 的 note-on 依規範等同
    note-off，這裡照這個規則處理，否則放開按鍵會被當成又按了一次。

    Split the 32-bit message winmm hands over into readable fields. Status,
    then data1, then data2, from the low byte up. A note-on with zero velocity
    means note-off by convention, and is treated that way here - otherwise
    releasing a pad reads as pressing it again.
    """
    try:
        packed = int(value)
    except (TypeError, ValueError):
        return None
    status = packed & 0xFF
    data1 = (packed >> 8) & 0x7F
    data2 = (packed >> 16) & 0x7F
    kind_bits = status & 0xF0
    channel = status & 0x0F
    if kind_bits == CONTROL_CHANGE:
        return {"kind": KIND_CONTROL, "channel": channel, "number": data1, "value": data2}
    if kind_bits in (NOTE_ON, NOTE_OFF):
        pressed = kind_bits == NOTE_ON and data2 > 0
        return {"kind": KIND_NOTE, "channel": channel, "number": data1,
                "value": data2, "pressed": pressed}
    return None


def binding_key(message: Dict[str, Any]) -> str:
    """
    把一則訊息換成設定裡用的鍵，例如 "control:7" 或 "note:36"。頻道不放進去：
    多數控制器可以整台換頻道，綁定不該因此失效。
    The key a message maps to in settings, like "control:7" or "note:36". The
    channel is left out on purpose: most controllers can be switched to another
    channel wholesale, and a binding should survive that.
    """
    return f"{message.get('kind')}:{message.get('number')}"


def scaled_value(value: Any, low: float = 0.0, high: float = 1.0) -> float:
    """把 0~127 的 MIDI 值換算到指定範圍。"""
    try:
        number = max(0, min(127, int(value)))
    except (TypeError, ValueError):
        number = 0
    return low + (high - low) * (number / 127.0)


def list_devices() -> List[Tuple[int, str]]:
    """
    可用的 MIDI 輸入裝置 [(索引, 名稱)]；沒有或平台不支援回傳空清單。
    Available MIDI inputs as (index, name); [] when there are none.
    """
    if not available():
        return []
    try:
        import ctypes
        from ctypes import wintypes

        class MIDIINCAPS(ctypes.Structure):
            _fields_ = [
                ("wMid", wintypes.WORD), ("wPid", wintypes.WORD),
                ("vDriverVersion", wintypes.UINT), ("szPname", wintypes.WCHAR * 32),
                ("dwSupport", wintypes.DWORD),
            ]

        winmm = ctypes.windll.winmm
        devices = []
        for index in range(winmm.midiInGetNumDevs()):
            caps = MIDIINCAPS()
            if winmm.midiInGetDevCapsW(index, ctypes.byref(caps), ctypes.sizeof(caps)) == 0:
                devices.append((index, caps.szPname))
        return devices
    except Exception as error:  # pragma: no cover - Win32 boundary
        front_engine_logger.warning(f"[MidiInput] listing failed: {error!r}")
        return []


class MidiInput(QObject):
    """
    打開一個 MIDI 輸入。訊息是在 winmm 自己的執行緒上送達的，所以這裡以 Qt
    訊號發出，由呼叫端用 QueuedConnection 接回 UI 執行緒。在 winmm 的執行緒上
    開 QTimer 是不會觸發的——那條執行緒沒有事件迴圈。

    Open a MIDI input. Messages arrive on winmm's own thread, so they leave as
    a Qt signal for the caller to take back to the UI thread with a
    QueuedConnection. Starting a QTimer on winmm's thread never fires: it has
    no event loop.
    """

    message_received = Signal(dict)

    def __init__(self, on_message: Optional[Callable[[Dict[str, Any]], None]] = None,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._on_message = on_message
        self._handle = None
        self._callback = None
        self.last_error = ""

    @property
    def running(self) -> bool:
        return self._handle is not None

    def start(self, device_index: int = 0) -> bool:
        """開始接收；沒有裝置或開啟失敗回傳 False。"""
        if self.running:
            return True
        if not available():
            self.last_error = "MIDI input is Windows only"
            return False
        try:
            return self._open(int(device_index))
        except Exception as error:  # pragma: no cover - Win32 boundary
            self.last_error = str(error)
            front_engine_logger.warning(f"[MidiInput] open failed: {error!r}")
            self._handle = None
            return False

    def _open(self, device_index: int) -> bool:  # pragma: no cover - needs a device
        import ctypes
        from ctypes import wintypes

        winmm = ctypes.windll.winmm
        if winmm.midiInGetNumDevs() <= device_index:
            self.last_error = "no such MIDI device"
            return False

        proc = ctypes.WINFUNCTYPE(None, wintypes.HANDLE, wintypes.UINT,
                                  ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)

        def _callback(_handle, message, _instance, param1, _param2):
            if message == _MIM_DATA:
                self.handle_raw(param1)

        # 回呼必須自己留著參考，被回收掉的話 winmm 會呼叫到已釋放的記憶體
        # The callback must be kept alive: if it is collected, winmm calls into
        # freed memory.
        self._callback = proc(_callback)
        handle = wintypes.HANDLE()
        result = winmm.midiInOpen(ctypes.byref(handle), device_index,
                                  self._callback, None, _CALLBACK_FUNCTION)
        if result != 0:
            self.last_error = f"midiInOpen failed ({result})"
            self._callback = None
            return False
        winmm.midiInStart(handle)
        self._handle = handle
        front_engine_logger.info(f"[MidiInput] listening on device {device_index}")
        return True

    def stop(self) -> None:
        """停止接收並關閉裝置。"""
        handle, self._handle = self._handle, None
        if handle is None:
            self._callback = None
            return
        try:  # pragma: no cover - Win32 boundary
            import ctypes

            winmm = ctypes.windll.winmm
            winmm.midiInStop(handle)
            winmm.midiInReset(handle)
            winmm.midiInClose(handle)
        except Exception as error:  # pragma: no cover - Win32 boundary
            front_engine_logger.debug(f"[MidiInput] close failed: {error!r}")
        # 裝置關掉之後才放掉 callback。self._callback 是那個 trampoline 唯一的
        # 參考，裝置還在送訊息時就放掉，winmm 會呼叫進已釋放的記憶體——轉一下
        # 旋鈕每秒就是幾十則訊息，這個空窗不是理論問題。
        # Release the callback only once the device is closed. self._callback is
        # the trampoline's only reference, and dropping it while the device is
        # still delivering leaves winmm calling into freed memory - one turn of a
        # knob is dozens of messages, so that window is not theoretical.
        self._callback = None
        front_engine_logger.info("[MidiInput] stopped")

    def handle_raw(self, packed: Any) -> Optional[Dict[str, Any]]:
        """處理一則原始訊息（測試會直接呼叫）。"""
        message = parse_message(packed)
        if message is None:
            return None
        self.message_received.emit(message)
        if self._on_message is None:
            return message
        try:
            self._on_message(message)
        except Exception as error:  # pragma: no cover - defensive around callbacks
            front_engine_logger.warning(f"[MidiInput] callback failed: {error!r}")
        return message
