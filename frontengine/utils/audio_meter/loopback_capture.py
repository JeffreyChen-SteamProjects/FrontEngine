"""
WASAPI 回送擷取：把「正在播出去的聲音」讀進來做頻譜。

**請注意這和本專案其他音訊功能不同。** 寵物與桌布的律動只讀 WASAPI 的
*電表數值*（一個 0~1 的音量），完全沒有音訊內容；頻譜視覺化做不到這件事——
要算頻率就必須真的拿到取樣資料，所以這個模組會擷取系統輸出的音訊串流。

擷取到的樣本只留在記憶體裡、只用來算 FFT，**不會寫檔、不會傳出去**，關掉
視覺化就停止擷取。僅 Windows 有效，其他平台 available() 一律為 False。

WASAPI loopback capture: read what is being played so it can be turned into a
spectrum.

**This differs from the rest of the audio features here.** The pet and the
wallpaper read only WASAPI's *meter* (a single 0..1 number) and never see audio
content. A spectrum cannot work that way - computing frequencies needs the
actual samples - so this module captures the system output stream.

Captured samples stay in memory, are used only for the FFT, are **never written
to disk or sent anywhere**, and capture stops the moment the visualiser is
turned off. Windows only; available() is False everywhere else.
"""
from __future__ import annotations

import sys
import threading
from typing import List, Optional

import numpy

from frontengine.utils.audio_meter.spectrum_analyzer import (
    DEFAULT_BANDS, clamp_bands, spectrum_bands,
)
from frontengine.utils.audio_meter.system_audio_meter import (
    activate_interface, open_render_endpoint,
)
from frontengine.utils.logging.loggin_instance import front_engine_logger

_IID_IAudioClient = "{1CB9AD4C-DBFA-4C32-B178-C2F568A703B2}"
_IID_IAudioCaptureClient = "{C8ADBD64-E71E-48A0-A4DE-185C395CD317}"
_AUDCLNT_SHAREMODE_SHARED = 0
_AUDCLNT_STREAMFLAGS_LOOPBACK = 0x00020000
_AUDCLNT_BUFFERFLAGS_SILENT = 0x2
# 緩衝長度（100 奈秒為單位）＝ 0.2 秒
# Buffer duration in 100-nanosecond units: 0.2 seconds.
_BUFFER_DURATION = 2_000_000
_WAVE_FORMAT_IEEE_FLOAT = 3
_WAVE_FORMAT_EXTENSIBLE = 0xFFFE
_POLL_SECONDS = 0.02


def available() -> bool:
    """這台機器能不能做回送擷取（只有 Windows 可以）。"""
    return sys.platform == "win32"


def samples_from_buffer(raw: bytes, bits_per_sample: int) -> numpy.ndarray:
    """
    把裝置給的原始位元組換成 -1~1 的浮點樣本。不認得的位元深度回傳空陣列。
    Raw device bytes to floats in -1..1; an unknown bit depth gives an empty array.
    """
    if not raw:
        return numpy.zeros(0, dtype=numpy.float32)
    if bits_per_sample == 32:
        return numpy.frombuffer(raw, dtype=numpy.float32)
    if bits_per_sample == 16:
        return numpy.frombuffer(raw, dtype=numpy.int16).astype(numpy.float32) / 32768.0
    front_engine_logger.warning(f"[LoopbackCapture] unsupported bit depth: {bits_per_sample}")
    return numpy.zeros(0, dtype=numpy.float32)


class _MixFormat:
    """從 WAVEFORMATEX 讀出來的幾個我們真的會用到的欄位。"""

    def __init__(self, channels: int, sample_rate: int, bits_per_sample: int,
                 block_align: int) -> None:
        self.channels = max(1, int(channels))
        self.sample_rate = max(8000, int(sample_rate))
        self.bits_per_sample = int(bits_per_sample)
        self.block_align = max(1, int(block_align))


class LoopbackSpectrum:
    """
    在背景執行緒擷取系統輸出並算成頻段強度；UI 用 bands() 取最新一組值。
    資料只在記憶體中流動，stop() 之後就不再擷取。

    Capture the system output on a background thread and reduce it to band
    levels; the UI reads the latest set with bands(). Nothing leaves memory, and
    stop() ends the capture.
    """

    def __init__(self, bands: int = DEFAULT_BANDS, device_id: Optional[str] = None) -> None:
        self.band_count = clamp_bands(bands)
        self.device_id = device_id
        self._lock = threading.Lock()
        self._bands: List[float] = [0.0] * self.band_count
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def set_bands(self, bands: int) -> None:
        """改變頻段數量（下一次擷取結果就會照新的算）。"""
        self.band_count = clamp_bands(bands)
        with self._lock:
            self._bands = [0.0] * self.band_count

    def bands(self) -> List[float]:
        """最新一組頻段強度；沒在跑或還沒讀到就是一排 0。"""
        with self._lock:
            return list(self._bands)

    def start(self) -> bool:
        """開始擷取；平台不支援或啟動失敗回傳 False。"""
        if self._running:
            return True
        if not available():
            front_engine_logger.info("[LoopbackCapture] not available on this platform")
            return False
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="frontengine-loopback", daemon=True)
        self._running = True
        self._thread.start()
        front_engine_logger.info("[LoopbackCapture] start")
        return True

    def stop(self) -> None:
        """停止擷取並等背景執行緒收工。"""
        if not self._running:
            return
        front_engine_logger.info("[LoopbackCapture] stop")
        self._stop_event.set()
        thread, self._thread = self._thread, None
        self._running = False
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)
        with self._lock:
            self._bands = [0.0] * self.band_count

    def _run(self) -> None:
        try:
            self._capture_loop()
        except Exception as error:  # pragma: no cover - COM boundary
            front_engine_logger.warning(f"[LoopbackCapture] capture failed: {error!r}")
        finally:
            self._running = False

    def _capture_loop(self) -> None:  # pragma: no cover - needs a real audio device
        tools, enumerator, device = open_render_endpoint(self.device_id)
        client = capture_client = None
        try:
            client = activate_interface(tools, device, _IID_IAudioClient)
            mix_format, format_pointer = self._mix_format(tools, client)
            self._initialise(tools, client, format_pointer)
            capture_client = self._service(tools, client)
            self._pump(tools, client, capture_client, mix_format)
        finally:
            for interface in (capture_client, client, device, enumerator):
                try:
                    tools.release(interface)
                except Exception as error:
                    front_engine_logger.debug(f"[LoopbackCapture] release failed: {error!r}")

    def _mix_format(self, tools, client):  # pragma: no cover - needs a real audio device
        """問裝置目前的混音格式，並保留 COM 配置的指標供 Initialize 使用。"""
        ctypes = tools.ctypes

        class _WAVEFORMATEX(ctypes.Structure):
            _fields_ = [
                ("wFormatTag", ctypes.c_uint16), ("nChannels", ctypes.c_uint16),
                ("nSamplesPerSec", ctypes.c_uint32), ("nAvgBytesPerSec", ctypes.c_uint32),
                ("nBlockAlign", ctypes.c_uint16), ("wBitsPerSample", ctypes.c_uint16),
                ("cbSize", ctypes.c_uint16),
            ]

        pointer = ctypes.POINTER(_WAVEFORMATEX)()
        get_mix_format = tools.method(
            client, 8, ctypes.HRESULT, [ctypes.POINTER(ctypes.POINTER(_WAVEFORMATEX))])
        if get_mix_format(client, ctypes.byref(pointer)) != 0 or not pointer:
            raise OSError("GetMixFormat failed")
        wave = pointer.contents
        if wave.wFormatTag not in (_WAVE_FORMAT_IEEE_FLOAT, _WAVE_FORMAT_EXTENSIBLE) \
                and wave.wBitsPerSample not in (16, 32):
            raise OSError(f"unsupported mix format tag {wave.wFormatTag}")
        return (_MixFormat(wave.nChannels, wave.nSamplesPerSec,
                           wave.wBitsPerSample, wave.nBlockAlign), pointer)

    @staticmethod
    def _initialise(tools, client, format_pointer) -> None:  # pragma: no cover - real device
        ctypes = tools.ctypes
        initialize = tools.method(
            client, 3, ctypes.HRESULT,
            [ctypes.c_int, ctypes.c_uint32, ctypes.c_int64, ctypes.c_int64,
             ctypes.c_void_p, ctypes.c_void_p])
        result = initialize(client, _AUDCLNT_SHAREMODE_SHARED, _AUDCLNT_STREAMFLAGS_LOOPBACK,
                            _BUFFER_DURATION, 0, ctypes.cast(format_pointer, ctypes.c_void_p), None)
        if result != 0:
            raise OSError(f"IAudioClient::Initialize failed (0x{result & 0xFFFFFFFF:08X})")

    @staticmethod
    def _service(tools, client):  # pragma: no cover - needs a real audio device
        ctypes = tools.ctypes
        capture_client = ctypes.c_void_p()
        iid = tools.guid(_IID_IAudioCaptureClient)
        get_service = tools.method(
            client, 14, ctypes.HRESULT,
            [ctypes.POINTER(tools.GUID), ctypes.POINTER(ctypes.c_void_p)])
        if get_service(client, ctypes.byref(iid),
                       ctypes.byref(capture_client)) != 0 or not capture_client.value:
            raise OSError("GetService(IAudioCaptureClient) failed")
        return capture_client

    def _pump(self, tools, client, capture_client,
              mix_format: _MixFormat) -> None:  # pragma: no cover - needs a real device
        """擷取迴圈：每輪把可讀的封包收完，算一次頻譜，然後短暫休息。"""
        ctypes = tools.ctypes
        start = tools.method(client, 10, ctypes.HRESULT, [])
        stop = tools.method(client, 11, ctypes.HRESULT, [])
        next_packet = tools.method(
            capture_client, 5, ctypes.HRESULT, [ctypes.POINTER(ctypes.c_uint32)])
        get_buffer = tools.method(
            capture_client, 3, ctypes.HRESULT,
            [ctypes.POINTER(ctypes.POINTER(ctypes.c_byte)), ctypes.POINTER(ctypes.c_uint32),
             ctypes.POINTER(ctypes.c_uint32), ctypes.c_void_p, ctypes.c_void_p])
        release_buffer = tools.method(
            capture_client, 4, ctypes.HRESULT, [ctypes.c_uint32])
        if start(client) != 0:
            raise OSError("IAudioClient::Start failed")
        try:
            while not self._stop_event.is_set():
                chunk = self._drain(ctypes, next_packet, get_buffer, release_buffer,
                                    capture_client, mix_format)
                if chunk.size:
                    self._store(spectrum_bands(chunk, mix_format.sample_rate,
                                               self.band_count, mix_format.channels))
                self._stop_event.wait(_POLL_SECONDS)
        finally:
            stop(client)

    @staticmethod
    def _drain(ctypes, next_packet, get_buffer, release_buffer, capture_client,
               mix_format: _MixFormat) -> numpy.ndarray:  # pragma: no cover - real device
        """把目前排隊的封包全部讀完，串成一段樣本。"""
        collected = []
        frames = ctypes.c_uint32()
        while next_packet(capture_client, ctypes.byref(frames)) == 0 and frames.value:
            data = ctypes.POINTER(ctypes.c_byte)()
            read = ctypes.c_uint32()
            flags = ctypes.c_uint32()
            if get_buffer(capture_client, ctypes.byref(data), ctypes.byref(read),
                          ctypes.byref(flags), None, None) != 0:
                break
            if read.value and not (flags.value & _AUDCLNT_BUFFERFLAGS_SILENT):
                raw = ctypes.string_at(data, read.value * mix_format.block_align)
                collected.append(samples_from_buffer(raw, mix_format.bits_per_sample))
            release_buffer(capture_client, read.value)
        if not collected:
            return numpy.zeros(0, dtype=numpy.float32)
        return numpy.concatenate(collected)

    def _store(self, bands: List[float]) -> None:
        with self._lock:
            self._bands = list(bands)
