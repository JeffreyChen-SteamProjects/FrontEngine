"""
以 WASAPI 的 IAudioMeterInformation::GetPeakValue 讀取「預設輸出裝置」的
峰值電表 (0~1)。這只是讀取電表數值，不擷取或錄製任何音訊內容（隱私友善），
僅 Windows 有效，任何失敗都退化為 None。

Read the default output device's peak meter (0..1) via WASAPI's
IAudioMeterInformation::GetPeakValue. This only reads a meter value — it does
NOT capture or record any audio content. Windows only; degrades to None.
"""
from __future__ import annotations

import sys
import uuid
from typing import Optional

from frontengine.utils.logging.loggin_instance import front_engine_logger

# WASAPI / Core Audio identifiers
_CLSID_MMDeviceEnumerator = "{BCDE0395-E52F-467C-8E3D-C4579291692E}"
_IID_IMMDeviceEnumerator = "{A95664D2-9614-4F35-A746-DE8DB63617E6}"
_IID_IAudioMeterInformation = "{C02216F6-8C67-4B5B-9D00-D008E73E0064}"
_CLSCTX_ALL = 23
_E_RENDER = 0   # audio output
_E_CONSOLE = 0  # default role


class SystemAudioMeter:
    """讀取系統輸出峰值電表；建立失敗或非 Windows 時 level() 回傳 None。"""

    def __init__(self) -> None:
        self._ok = False
        self._meter = None
        self._device = None
        self._enumerator = None
        self._get_peak = None
        self._byref = None
        self._c_float = None
        self._release_method = None
        if sys.platform == "win32":
            try:
                self._init()
                self._ok = True
            except Exception as error:  # pragma: no cover - COM boundary
                front_engine_logger.warning(f"[SystemAudioMeter] init failed: {error!r}")
                self._release_all()

    # --- COM plumbing -------------------------------------------------
    def _init(self) -> None:
        import ctypes
        from ctypes import POINTER, byref, c_float, c_void_p, c_ulong, HRESULT
        from ctypes.wintypes import DWORD

        class _GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", ctypes.c_uint32),
                ("Data2", ctypes.c_uint16),
                ("Data3", ctypes.c_uint16),
                ("Data4", ctypes.c_uint8 * 8),
            ]

        def guid(text: str) -> "_GUID":
            value = _GUID()
            ctypes.memmove(byref(value), uuid.UUID(text).bytes_le, ctypes.sizeof(value))
            return value

        def method(iface, index, restype, argtypes):
            vtable = ctypes.cast(iface, POINTER(POINTER(c_void_p)))
            func_address = vtable[0][index]
            proto = ctypes.WINFUNCTYPE(restype, c_void_p, *argtypes)
            return proto(func_address)

        ole32 = ctypes.windll.ole32
        ole32.CoInitialize(None)  # S_FALSE if already initialised; harmless

        enumerator = c_void_p()
        clsid = guid(_CLSID_MMDeviceEnumerator)
        iid_enum = guid(_IID_IMMDeviceEnumerator)
        if ole32.CoCreateInstance(byref(clsid), None, _CLSCTX_ALL, byref(iid_enum), byref(enumerator)) != 0 \
                or not enumerator.value:
            raise OSError("CoCreateInstance(MMDeviceEnumerator) failed")
        self._enumerator = enumerator

        device = c_void_p()
        get_default = method(enumerator, 4, HRESULT, [DWORD, DWORD, POINTER(c_void_p)])
        if get_default(enumerator, _E_RENDER, _E_CONSOLE, byref(device)) != 0 or not device.value:
            raise OSError("GetDefaultAudioEndpoint failed")
        self._device = device

        meter = c_void_p()
        iid_meter = guid(_IID_IAudioMeterInformation)
        activate = method(device, 3, HRESULT, [POINTER(_GUID), DWORD, c_void_p, POINTER(c_void_p)])
        if activate(device, byref(iid_meter), _CLSCTX_ALL, None, byref(meter)) != 0 or not meter.value:
            raise OSError("Activate(IAudioMeterInformation) failed")
        self._meter = meter

        self._get_peak = method(meter, 3, HRESULT, [POINTER(c_float)])
        self._byref = byref
        self._c_float = c_float
        self._release_method = lambda iface: method(iface, 2, c_ulong, [])

    def level(self) -> Optional[float]:
        """回傳目前輸出峰值 0~1，或 None。"""
        if not self._ok or self._meter is None or self._get_peak is None:
            return None
        try:
            peak = self._c_float()
            if self._get_peak(self._meter, self._byref(peak)) != 0:
                return None
            return max(0.0, min(1.0, float(peak.value)))
        except Exception:  # pragma: no cover - COM boundary
            return None

    def _release_all(self) -> None:
        for iface in (self._meter, self._device, self._enumerator):
            if iface is not None and getattr(iface, "value", None) and self._release_method is not None:
                try:
                    self._release_method(iface)(iface)
                except Exception:
                    pass
        self._meter = self._device = self._enumerator = None
        self._ok = False


_meter_singleton: Optional[SystemAudioMeter] = None


def system_audio_level() -> Optional[float]:
    """便利函式：以單例電表回傳目前系統輸出峰值 0~1，或 None。"""
    global _meter_singleton
    if sys.platform != "win32":
        return None
    if _meter_singleton is None:
        _meter_singleton = SystemAudioMeter()
    return _meter_singleton.level()
