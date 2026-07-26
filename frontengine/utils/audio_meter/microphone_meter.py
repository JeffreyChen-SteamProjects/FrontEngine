"""
麥克風音量電表：讀輸入裝置的峰值，用來讓寵物跟著你說話開合嘴巴。

和喇叭那支電表一樣，**只讀電表數值、不擷取任何音訊內容**——這裡拿到的是一個
0~1 的數字，不是聲音。頻譜那種需要取樣資料的功能才會真的擷取音訊，兩者是
不同的東西。僅 Windows 有效，其餘平台一律回傳 None。

A microphone meter: read the input device's peak so the pet can move its mouth
while you talk.

Like the speaker meter, this **reads a meter value and captures no audio
content** - what comes back is a number between 0 and 1, not sound. Only the
spectrum, which needs samples, actually captures audio; these are different
things. Windows only; None everywhere else.
"""
from __future__ import annotations

import sys
from typing import List, Optional, Tuple

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.audio_meter.system_audio_meter import (
    _DEVICE_STATE_ACTIVE, _IID_IAudioMeterInformation, _collect_devices,
    _com_tools, _create_enumerator, activate_interface,
)

# EDataFlow：0 是輸出（喇叭），1 是輸入（麥克風）
# EDataFlow: 0 is render (speakers), 1 is capture (microphones).
_E_CAPTURE = 1


def list_input_devices() -> List[Tuple[str, str]]:
    """
    目前啟用中的輸入裝置 [(device_id, 顯示名稱)]；非 Windows 或失敗回傳 []。
    Active input devices as (device_id, friendly_name); [] when unavailable.
    """
    if sys.platform != "win32":
        return []
    enumerator = None
    collection = None
    tools = None
    try:
        tools = _com_tools()
        ctypes = tools.ctypes
        from ctypes.wintypes import DWORD

        enumerator = _create_enumerator(tools)
        collection = ctypes.c_void_p()
        enum_endpoints = tools.method(
            enumerator, 3, ctypes.HRESULT, [DWORD, DWORD, ctypes.POINTER(ctypes.c_void_p)])
        if enum_endpoints(enumerator, _E_CAPTURE, _DEVICE_STATE_ACTIVE,
                          ctypes.byref(collection)) != 0 or not collection.value:
            return []
        return _collect_devices(tools, collection)
    except Exception as error:  # pragma: no cover - COM boundary
        front_engine_logger.warning(f"[MicrophoneMeter] listing failed: {error!r}")
        return []
    finally:
        if tools is not None:
            tools.release(collection)
            tools.release(enumerator)


class MicrophoneMeter:
    """
    讀某個輸入裝置的峰值電表。device_id 為 None 時取預設麥克風；
    建立失敗或非 Windows 時 level() 一律回傳 None。
    """

    def __init__(self, device_id: Optional[str] = None) -> None:
        self.device_id = device_id
        self._tools = None
        self._meter = None
        self._device = None
        self._enumerator = None
        self._get_peak = None
        self._ok = False
        if sys.platform == "win32":
            try:
                self._open()
                self._ok = True
            except Exception as error:  # pragma: no cover - COM boundary
                front_engine_logger.warning(f"[MicrophoneMeter] init failed: {error!r}")
                self.close()

    def _open(self) -> None:
        tools = _com_tools()
        self._tools = tools
        ctypes = tools.ctypes
        from ctypes.wintypes import DWORD

        self._enumerator = _create_enumerator(tools)
        device = ctypes.c_void_p()
        if self.device_id:
            get_device = tools.method(
                self._enumerator, 5, ctypes.HRESULT,
                [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_void_p)])
            result = get_device(self._enumerator, self.device_id, ctypes.byref(device))
        else:
            get_default = tools.method(
                self._enumerator, 4, ctypes.HRESULT,
                [DWORD, DWORD, ctypes.POINTER(ctypes.c_void_p)])
            result = get_default(self._enumerator, _E_CAPTURE, 0, ctypes.byref(device))
        if result != 0 or not device.value:
            raise OSError(f"resolve input endpoint failed (device_id={self.device_id!r})")
        self._device = device
        self._meter = activate_interface(tools, device, _IID_IAudioMeterInformation)
        self._get_peak = tools.method(
            self._meter, 3, ctypes.HRESULT, [ctypes.POINTER(ctypes.c_float)])

    def level(self) -> Optional[float]:
        """目前麥克風的峰值 0~1；不可用時回傳 None。"""
        if not self._ok or self._meter is None or self._get_peak is None:
            return None
        try:
            peak = self._tools.ctypes.c_float()
            if self._get_peak(self._meter, self._tools.ctypes.byref(peak)) != 0:
                return None
            return max(0.0, min(1.0, float(peak.value)))
        except Exception:  # pragma: no cover - COM boundary
            return None

    def close(self) -> None:
        """釋放 COM 介面；可重複呼叫。"""
        for interface in (self._meter, self._device, self._enumerator):
            if self._tools is None:
                break
            try:
                self._tools.release(interface)
            except Exception as error:  # pragma: no cover - COM boundary
                front_engine_logger.debug(f"[MicrophoneMeter] release failed: {error!r}")
        self._meter = self._device = self._enumerator = None
        self._get_peak = None
        self._ok = False


_meter_singleton: Optional[MicrophoneMeter] = None


def microphone_level() -> Optional[float]:
    """便利函式：以共用電表回傳預設麥克風的峰值 0~1，或 None。"""
    global _meter_singleton
    if sys.platform != "win32":
        return None
    if _meter_singleton is None:
        _meter_singleton = MicrophoneMeter()
    return _meter_singleton.level()
