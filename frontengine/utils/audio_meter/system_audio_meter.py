"""
以 WASAPI 的 IAudioMeterInformation::GetPeakValue 讀取輸出裝置的峰值電表 (0~1)。
可讀「預設輸出裝置」，也可指定某個輸出端點（例如某台螢幕的喇叭）。這只是讀取
電表數值，不擷取或錄製任何音訊內容（隱私友善），僅 Windows 有效，任何失敗都退化為 None。

Read an output device's peak meter (0..1) via WASAPI's
IAudioMeterInformation::GetPeakValue — either the default endpoint or a named
one (e.g. a particular monitor's speakers). This only reads a meter value — it
does NOT capture or record any audio content. Windows only; degrades to None.
"""
from __future__ import annotations

import sys
import uuid
from typing import List, Optional, Tuple

from frontengine.utils.logging.loggin_instance import front_engine_logger

# WASAPI / Core Audio identifiers
_CLSID_MMDeviceEnumerator = "{BCDE0395-E52F-467C-8E3D-C4579291692E}"
_IID_IMMDeviceEnumerator = "{A95664D2-9614-4F35-A746-DE8DB63617E6}"
_IID_IAudioMeterInformation = "{C02216F6-8C67-4B5B-9D00-D008E73E0064}"
_PKEY_DEVICE_FRIENDLY_NAME_FMTID = "{A45C254E-DF1C-4EFD-8020-67D146A850E0}"
_PKEY_DEVICE_FRIENDLY_NAME_PID = 14
_CLSCTX_ALL = 23
_E_RENDER = 0            # audio output
_E_CONSOLE = 0           # default role
_DEVICE_STATE_ACTIVE = 1
_STGM_READ = 0
_VT_LPWSTR = 31

_com_tools_cache = None


def _com_tools():
    """延遲建立並快取 ctypes COM 小工具（僅 Windows 會走到）。"""
    global _com_tools_cache
    if _com_tools_cache is None:
        _com_tools_cache = _build_com_tools()
    return _com_tools_cache


def _build_com_tools():
    import ctypes
    from types import SimpleNamespace

    class _GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", ctypes.c_uint32),
            ("Data2", ctypes.c_uint16),
            ("Data3", ctypes.c_uint16),
            ("Data4", ctypes.c_uint8 * 8),
        ]

    class _PROPERTYKEY(ctypes.Structure):
        _fields_ = [("fmtid", _GUID), ("pid", ctypes.c_uint32)]

    class _PROPVARIANT(ctypes.Structure):
        _fields_ = [
            ("vt", ctypes.c_ushort),
            ("reserved1", ctypes.c_ushort),
            ("reserved2", ctypes.c_ushort),
            ("reserved3", ctypes.c_ushort),
            ("data", ctypes.c_void_p),
            ("padding", ctypes.c_void_p),
        ]

    def guid(text: str) -> "_GUID":
        value = _GUID()
        ctypes.memmove(ctypes.byref(value), uuid.UUID(text).bytes_le, ctypes.sizeof(value))
        return value

    def method(iface, index, restype, argtypes):
        vtable = ctypes.cast(iface, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))
        proto = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
        return proto(vtable[0][index])

    def release(iface) -> None:
        if iface is not None and getattr(iface, "value", None):
            method(iface, 2, ctypes.c_ulong, [])(iface)

    return SimpleNamespace(
        ctypes=ctypes, ole32=ctypes.windll.ole32, GUID=_GUID, PROPERTYKEY=_PROPERTYKEY,
        PROPVARIANT=_PROPVARIANT, guid=guid, method=method, release=release,
    )


def _create_enumerator(tools):
    """建立 IMMDeviceEnumerator；失敗擲出 OSError。"""
    ctypes = tools.ctypes
    tools.ole32.CoInitialize(None)  # S_FALSE if already initialised; harmless
    enumerator = ctypes.c_void_p()
    clsid = tools.guid(_CLSID_MMDeviceEnumerator)
    iid = tools.guid(_IID_IMMDeviceEnumerator)
    created = tools.ole32.CoCreateInstance(
        ctypes.byref(clsid), None, _CLSCTX_ALL, ctypes.byref(iid), ctypes.byref(enumerator))
    if created != 0 or not enumerator.value:
        raise OSError("CoCreateInstance(MMDeviceEnumerator) failed")
    return enumerator


def _endpoint(tools, enumerator, device_id: Optional[str]):
    """取得輸出端點：device_id 為 None 時取預設裝置。失敗擲出 OSError。"""
    ctypes = tools.ctypes
    device = ctypes.c_void_p()
    if device_id:
        get_device = tools.method(
            enumerator, 5, ctypes.HRESULT, [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_void_p)])
        result = get_device(enumerator, device_id, ctypes.byref(device))
    else:
        from ctypes.wintypes import DWORD

        get_default = tools.method(
            enumerator, 4, ctypes.HRESULT, [DWORD, DWORD, ctypes.POINTER(ctypes.c_void_p)])
        result = get_default(enumerator, _E_RENDER, _E_CONSOLE, ctypes.byref(device))
    if result != 0 or not device.value:
        raise OSError(f"resolve endpoint failed (device_id={device_id!r})")
    return device


def open_render_endpoint(device_id: Optional[str] = None):
    """
    開啟一個輸出端點，回傳 (tools, enumerator, device)；呼叫端要負責用
    tools.release() 釋放後兩者。非 Windows 或失敗時擲出 OSError。
    Open an output endpoint and hand back (tools, enumerator, device). The
    caller releases the last two via tools.release(). Raises OSError when it
    cannot be done - including on every non-Windows platform.
    """
    if sys.platform != "win32":
        raise OSError("WASAPI endpoints are Windows only")
    tools = _com_tools()
    enumerator = _create_enumerator(tools)
    try:
        device = _endpoint(tools, enumerator, device_id)
    except Exception:
        tools.release(enumerator)
        raise
    return (tools, enumerator, device)


def activate_interface(tools, device, iid_text: str):
    """在端點上啟用一個介面（IAudioClient 等），失敗擲出 OSError。"""
    ctypes = tools.ctypes
    from ctypes.wintypes import DWORD

    interface = ctypes.c_void_p()
    iid = tools.guid(iid_text)
    activate = tools.method(
        device, 3, ctypes.HRESULT,
        [ctypes.POINTER(tools.GUID), DWORD, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)])
    if activate(device, ctypes.byref(iid), _CLSCTX_ALL, None,
                ctypes.byref(interface)) != 0 or not interface.value:
        raise OSError(f"Activate({iid_text}) failed")
    return interface


def query_interface(tools, interface, iid_text: str):
    """
    對已有的介面做 QueryInterface，取得它的另一個面向（例如把
    IAudioSessionControl 換成 IAudioSessionControl2）。取不到回傳 None。
    QueryInterface an existing pointer for another facet of the same object -
    IAudioSessionControl to IAudioSessionControl2, say. None when unsupported.
    """
    ctypes = tools.ctypes
    result_interface = ctypes.c_void_p()
    iid = tools.guid(iid_text)
    query = tools.method(
        interface, 0, ctypes.HRESULT,
        [ctypes.POINTER(tools.GUID), ctypes.POINTER(ctypes.c_void_p)])
    if query(interface, ctypes.byref(iid), ctypes.byref(result_interface)) != 0 \
            or not result_interface.value:
        return None
    return result_interface


def _read_device_id(tools, device) -> Optional[str]:
    """讀取端點的裝置 ID 字串（COM 配置的記憶體會釋放）。"""
    ctypes = tools.ctypes
    buffer = ctypes.c_void_p()
    get_id = tools.method(device, 5, ctypes.HRESULT, [ctypes.POINTER(ctypes.c_void_p)])
    if get_id(device, ctypes.byref(buffer)) != 0 or not buffer.value:
        return None
    value = ctypes.wstring_at(buffer.value)
    tools.ole32.CoTaskMemFree(buffer)
    return value


def _read_friendly_name(tools, device) -> Optional[str]:
    """讀取端點的顯示名稱，例如「Speakers (Realtek(R) Audio)」。"""
    ctypes = tools.ctypes
    from ctypes.wintypes import DWORD

    store = ctypes.c_void_p()
    open_store = tools.method(
        device, 4, ctypes.HRESULT, [DWORD, ctypes.POINTER(ctypes.c_void_p)])
    if open_store(device, _STGM_READ, ctypes.byref(store)) != 0 or not store.value:
        return None
    try:
        key = tools.PROPERTYKEY()
        key.fmtid = tools.guid(_PKEY_DEVICE_FRIENDLY_NAME_FMTID)
        key.pid = _PKEY_DEVICE_FRIENDLY_NAME_PID
        value = tools.PROPVARIANT()
        get_value = tools.method(
            store, 5, ctypes.HRESULT,
            [ctypes.POINTER(tools.PROPERTYKEY), ctypes.POINTER(tools.PROPVARIANT)])
        if get_value(store, ctypes.byref(key), ctypes.byref(value)) != 0:
            return None
        name = ctypes.wstring_at(value.data) if value.vt == _VT_LPWSTR and value.data else None
        tools.ole32.PropVariantClear(ctypes.byref(value))
        return name
    finally:
        tools.release(store)


def list_output_devices() -> List[Tuple[str, str]]:
    """
    列出目前啟用中的輸出端點 [(device_id, friendly_name)]；非 Windows 或失敗回傳 []。
    List active output endpoints as (device_id, friendly_name); [] when unavailable.
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
        if enum_endpoints(enumerator, _E_RENDER, _DEVICE_STATE_ACTIVE,
                          ctypes.byref(collection)) != 0 or not collection.value:
            return []
        return _collect_devices(tools, collection)
    except Exception as error:  # pragma: no cover - COM boundary
        front_engine_logger.warning(f"[list_output_devices] failed: {error!r}")
        return []
    finally:
        if tools is not None:
            tools.release(collection)
            tools.release(enumerator)


def _collect_devices(tools, collection) -> List[Tuple[str, str]]:
    """走訪 IMMDeviceCollection，收集 (device_id, friendly_name)。"""
    ctypes = tools.ctypes
    count = ctypes.c_uint32()
    get_count = tools.method(collection, 3, ctypes.HRESULT, [ctypes.POINTER(ctypes.c_uint32)])
    if get_count(collection, ctypes.byref(count)) != 0:
        return []
    item = tools.method(
        collection, 4, ctypes.HRESULT, [ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p)])
    devices: List[Tuple[str, str]] = []
    for index in range(int(count.value)):
        device = ctypes.c_void_p()
        if item(collection, index, ctypes.byref(device)) != 0 or not device.value:
            continue
        try:
            device_id = _read_device_id(tools, device)
            name = _read_friendly_name(tools, device)
            if device_id:
                devices.append((device_id, name or device_id))
        finally:
            tools.release(device)
    return devices


class SystemAudioMeter:
    """
    讀取某個輸出端點的峰值電表；device_id 為 None 時讀預設輸出裝置。
    建立失敗或非 Windows 時 level() 回傳 None。
    """

    def __init__(self, device_id: Optional[str] = None) -> None:
        self.device_id = device_id
        self._ok = False
        self._tools = None
        self._meter = None
        self._device = None
        self._enumerator = None
        self._get_peak = None
        if sys.platform == "win32":
            try:
                self._init()
                self._ok = True
            except Exception as error:  # pragma: no cover - COM boundary
                front_engine_logger.warning(
                    f"[SystemAudioMeter] init failed (device_id={device_id!r}): {error!r}")
                self.close()

    def _init(self) -> None:
        tools = _com_tools()
        self._tools = tools
        ctypes = tools.ctypes
        from ctypes.wintypes import DWORD

        self._enumerator = _create_enumerator(tools)
        self._device = _endpoint(tools, self._enumerator, self.device_id)

        meter = ctypes.c_void_p()
        iid_meter = tools.guid(_IID_IAudioMeterInformation)
        activate = tools.method(
            self._device, 3, ctypes.HRESULT,
            [ctypes.POINTER(tools.GUID), DWORD, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)])
        if activate(self._device, ctypes.byref(iid_meter), _CLSCTX_ALL, None,
                    ctypes.byref(meter)) != 0 or not meter.value:
            raise OSError("Activate(IAudioMeterInformation) failed")
        self._meter = meter
        self._get_peak = tools.method(
            meter, 3, ctypes.HRESULT, [ctypes.POINTER(ctypes.c_float)])

    def level(self) -> Optional[float]:
        """回傳目前輸出峰值 0~1，或 None。"""
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
        """釋放 COM 介面；可重複呼叫 / Release COM interfaces; safe to call twice."""
        for iface in (self._meter, self._device, self._enumerator):
            if self._tools is None:
                break
            try:
                self._tools.release(iface)
            except Exception as error:  # pragma: no cover - COM boundary
                # 釋放個別介面失敗不影響清理流程，記錄後繼續。
                # A single interface failing to release must not abort cleanup.
                front_engine_logger.debug(f"[SystemAudioMeter] release failed: {error!r}")
        self._meter = self._device = self._enumerator = None
        self._get_peak = None
        self._ok = False


_meter_singleton: Optional[SystemAudioMeter] = None


def system_audio_level() -> Optional[float]:
    """便利函式：以單例電表回傳預設輸出裝置的峰值 0~1，或 None。"""
    global _meter_singleton
    if sys.platform != "win32":
        return None
    if _meter_singleton is None:
        _meter_singleton = SystemAudioMeter()
    return _meter_singleton.level()
