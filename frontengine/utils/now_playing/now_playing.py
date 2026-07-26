"""
正在播放什麼：優先問 Windows 的媒體控制（SMTC），拿得到歌名與演出者；
沒有 WinRT 綁定時退而求其次，從 WASAPI 的音訊工作階段找出正在出聲的程式，
至少能顯示「Spotify 正在播放」。兩條路都不通就回傳 None。

What is playing: ask Windows' media controls (SMTC) first for a title and
artist. Without the WinRT bindings, fall back to WASAPI's audio sessions to at
least name the app making sound. When neither works, return None.

SMTC 需要 `winsdk`（或舊的 `winrt`）套件，本專案不強制安裝，因此只在有裝時
啟用；這是刻意的取捨，避免為了一個小功能增加必要相依。
SMTC needs the `winsdk` (or legacy `winrt`) package. It is deliberately not a
required dependency here - the feature simply uses it when present.
"""
from __future__ import annotations

import sys
from typing import Optional

from frontengine.utils.logging.loggin_instance import front_engine_logger

_IID_IAudioSessionManager2 = "{77AA99A0-1BD6-484F-8BC7-2C654C9A9B6F}"
_IID_IAudioSessionControl2 = "{BFB7FF88-7239-4FC9-8FA2-07C950BE9C6D}"
_IID_IAudioMeterInformation = "{C02216F6-8C67-4B5B-9D00-D008E73E0064}"
_SESSION_ENUMERATOR_INDEX = 5
# AudioSessionStateActive：這個工作階段正在出聲
# AudioSessionStateActive: this session is making sound right now.
_SESSION_STATE_ACTIVE = 1
# 低於這個電表值就當作沒在響：有些程式（例如通訊軟體）會一直掛著一條
# 幾乎全是零的串流，峰值大約 1e-10，那不是「正在播放」。
# Below this meter reading nothing is really sounding: some apps keep a
# near-silent stream open forever, peaking around 1e-10, which is not
# "now playing" by any useful definition.
_AUDIBLE_LEVEL = 1e-4


def format_now_playing(title: Optional[str], artist: Optional[str] = None,
                       app: Optional[str] = None) -> str:
    """
    把拿到的資訊排成一行字：有歌名就「演出者 - 歌名」，只知道程式就顯示程式名。
    Lay the pieces out on one line: "artist - title" when known, the app name
    when that is all we have, and an empty string when we know nothing.
    """
    title_text = str(title or "").strip()
    artist_text = str(artist or "").strip()
    app_text = str(app or "").strip()
    if title_text and artist_text:
        return f"{artist_text} - {title_text}"
    if title_text:
        return title_text
    return app_text


def _winrt_media_module():
    """匯入 SMTC 綁定；沒安裝就回傳 None（這是預期情況，不是錯誤）。"""
    for module_name in ("winsdk.windows.media.control", "winrt.windows.media.control"):
        try:
            return __import__(module_name, fromlist=["*"])
        except ImportError:
            continue
    return None


def smtc_now_playing() -> Optional[str]:
    """
    問 Windows 媒體控制目前播放的曲目；沒有 WinRT 綁定、沒有工作階段或
    任何失敗都回傳 None。
    """
    if sys.platform != "win32":
        return None
    module = _winrt_media_module()
    if module is None:
        return None
    try:
        import asyncio

        async def read() -> Optional[str]:
            manager_class = module.GlobalSystemMediaTransportControlsSessionManager
            manager = await manager_class.request_async()
            session = manager.get_current_session()
            if session is None:
                return None
            properties = await session.try_get_media_properties_async()
            return format_now_playing(properties.title, properties.artist) or None

        return asyncio.run(read())
    except Exception as error:  # pragma: no cover - depends on an optional package
        front_engine_logger.debug(f"[NowPlaying] SMTC unavailable: {error!r}")
        return None


def audio_session_app() -> Optional[str]:
    """
    退而求其次：找出目前正在出聲的程式名稱（WASAPI 音訊工作階段）。
    只讀工作階段的狀態與程序 ID，不碰任何音訊內容。
    The fallback: the name of the app currently making sound, from WASAPI's
    audio sessions. It reads session state and a process id - never audio.
    """
    if sys.platform != "win32":
        return None
    try:
        return _audio_session_app_windows()
    except Exception as error:  # pragma: no cover - COM boundary
        front_engine_logger.debug(f"[NowPlaying] audio session probe failed: {error!r}")
        return None


def _audio_session_app_windows() -> Optional[str]:  # pragma: no cover - needs a real device
    from frontengine.utils.audio_meter.system_audio_meter import (
        activate_interface, open_render_endpoint,
    )

    tools, enumerator, device = open_render_endpoint(None)
    manager = enumerator_interface = None
    ctypes = tools.ctypes
    try:
        manager = activate_interface(tools, device, _IID_IAudioSessionManager2)
        enumerator_interface = ctypes.c_void_p()
        get_session_enumerator = tools.method(
            manager, _SESSION_ENUMERATOR_INDEX, ctypes.HRESULT,
            [ctypes.POINTER(ctypes.c_void_p)])
        if get_session_enumerator(manager, ctypes.byref(enumerator_interface)) != 0 \
                or not enumerator_interface.value:
            return None
        return _loudest_active_session_app(tools, enumerator_interface, _SESSION_STATE_ACTIVE)
    finally:
        for interface in (enumerator_interface, manager, device, enumerator):
            try:
                tools.release(interface)
            except Exception as error:
                front_engine_logger.debug(f"[NowPlaying] release failed: {error!r}")


def _loudest_active_session_app(tools, session_enumerator,
                                active_state: int) -> Optional[str]:  # pragma: no cover - device
    """走訪音訊工作階段，回傳此刻聲音最大的那個程式名稱。"""
    from pathlib import Path

    ctypes = tools.ctypes
    count = ctypes.c_int()
    get_count = tools.method(
        session_enumerator, 3, ctypes.HRESULT, [ctypes.POINTER(ctypes.c_int)])
    if get_count(session_enumerator, ctypes.byref(count)) != 0:
        return None
    get_session = tools.method(
        session_enumerator, 4, ctypes.HRESULT,
        [ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)])
    # 同時可能有好幾個工作階段是「使用中」（有些只是開著沒在響），
    # 所以挑此刻電表最大的那個，才會是使用者真正在聽的東西。
    # Several sessions can be "active" while only one is audible, so pick the
    # loudest right now - that is what the user is actually listening to.
    best_name, best_level = None, -1.0
    for index in range(int(count.value)):
        control = ctypes.c_void_p()
        if get_session(session_enumerator, index, ctypes.byref(control)) != 0 or not control.value:
            continue
        try:
            state = ctypes.c_int()
            get_state = tools.method(control, 3, ctypes.HRESULT, [ctypes.POINTER(ctypes.c_int)])
            if get_state(control, ctypes.byref(state)) != 0 or state.value != active_state:
                continue
            name = _session_process_name(tools, control)
            if not name:
                continue
            level = _session_level(tools, control)
            if level > best_level:
                best_name, best_level = Path(name).stem, level
        finally:
            tools.release(control)
    # 全部都沒出聲（開著但暫停）就當作「沒有在播」
    # Every session silent - open but paused - counts as nothing playing.
    return best_name if best_level >= _AUDIBLE_LEVEL else None


def _session_process_name(tools, control) -> Optional[str]:  # pragma: no cover - real device
    """工作階段背後的執行檔路徑（程序 ID 只在 IAudioSessionControl2 上）。"""
    from frontengine.utils.audio_meter.system_audio_meter import query_interface

    ctypes = tools.ctypes
    control2 = query_interface(tools, control, _IID_IAudioSessionControl2)
    if control2 is None:
        return None
    try:
        process_id = ctypes.c_uint32()
        get_process_id = tools.method(
            control2, 14, ctypes.HRESULT, [ctypes.POINTER(ctypes.c_uint32)])
        if get_process_id(control2, ctypes.byref(process_id)) != 0 or not process_id.value:
            return None
        return _process_name(ctypes, int(process_id.value))
    finally:
        tools.release(control2)


def _session_level(tools, control) -> float:  # pragma: no cover - needs a real device
    """這個工作階段目前的峰值；問不到就當 0。"""
    from frontengine.utils.audio_meter.system_audio_meter import query_interface

    ctypes = tools.ctypes
    meter = query_interface(tools, control, _IID_IAudioMeterInformation)
    if meter is None:
        return 0.0
    try:
        peak = ctypes.c_float()
        get_peak = tools.method(meter, 3, ctypes.HRESULT, [ctypes.POINTER(ctypes.c_float)])
        if get_peak(meter, ctypes.byref(peak)) != 0:
            return 0.0
        return float(peak.value)
    finally:
        tools.release(meter)


def _process_name(ctypes, process_id: int) -> Optional[str]:  # pragma: no cover - Win32 boundary
    """由程序 ID 取得執行檔名稱（只要求最低限度的查詢權限）。"""
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(0x1000, False, process_id)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return None
    try:
        size = ctypes.c_uint32(260)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return None
        return buffer.value or None
    finally:
        kernel32.CloseHandle(handle)


def now_playing() -> Optional[str]:
    """
    目前正在播放的一行說明；SMTC 優先，退回「哪個程式在出聲」，都沒有就 None。
    """
    return smtc_now_playing() or format_now_playing(None, None, audio_session_app()) or None
