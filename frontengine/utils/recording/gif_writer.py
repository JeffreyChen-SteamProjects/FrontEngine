"""
最小的 GIF89a 編碼器：把一連串畫面寫成動畫 GIF。

為什麼要自己寫：Qt 只讀得懂 GIF、寫不出來，而螢幕錄影的輸出格式就是 GIF。
與其多一個「沒裝就不能用」的相依套件，不如把這段寫進來——規格固定、程式碼
不長，而且可以用 Qt 自己讀回來驗證。

顏色用固定的 6x6x6 色階加灰階（共 232 色）做最近色對應：螢幕錄影多半是介面
截圖，這樣的調色盤已經夠用，也省下每張畫面重新量化的成本。

A small GIF89a encoder: write a sequence of frames as an animated GIF.

Why write one: Qt reads GIF but cannot write it, and GIF is what a screen
recording should come out as. Rather than add a dependency that turns the
feature off when it is missing, the format is short and fixed - and the output
can be verified by reading it back with Qt.

Colours use a fixed 6x6x6 cube plus greys (232 entries) with nearest-colour
mapping: screen recordings are mostly interface captures, where that is plenty
and avoids re-quantising every frame.
"""
from __future__ import annotations

from collections import deque
from io import BytesIO
import os
from pathlib import Path
import tempfile
import threading
import time
from typing import Callable, Iterable, List, Optional, Sequence, Tuple

import numpy

_HEADER = b"GIF89a"
_TRAILER = b"\x3b"
_MIN_CODE_SIZE = 8
_CLEAR_CODE = 1 << _MIN_CODE_SIZE
_END_CODE = _CLEAR_CODE + 1
_CUBE_STEPS = (0, 51, 102, 153, 204, 255)
MIN_DELAY_MS = 20


def build_palette() -> List[Tuple[int, int, int]]:
    """
    固定調色盤：6x6x6 色階（216 色）＋ 16 階灰，共 232 色，其餘補黑。
    The fixed palette: a 6x6x6 cube (216) plus 16 greys, padded to 256.
    """
    palette = [(red, green, blue)
               for red in _CUBE_STEPS for green in _CUBE_STEPS for blue in _CUBE_STEPS]
    palette.extend((level, level, level) for level in range(8, 256, 16))
    palette.extend([(0, 0, 0)] * (256 - len(palette)))
    return palette[:256]


_PALETTE = build_palette()
# 距離要用 int32：色差平方最大 255^2 = 65025，int16 會溢位到負數，
# argmin 就會挑到完全不相干的顏色。
# Distances need int32: a squared channel difference reaches 255^2 = 65025,
# which overflows int16 into negatives and makes argmin pick nonsense.
_PALETTE_ARRAY = numpy.array(_PALETTE, dtype=numpy.int32)

# 查表用的顏色精度：每個通道取高 5 位（32 階）。
# Colour resolution of the lookup table: the top 5 bits per channel (32 steps).
_LOOKUP_BITS = 3
_LOOKUP_STEPS = 1 << (8 - _LOOKUP_BITS)
_LOOKUP_CHUNK = 4096
_lookup_table: Optional[numpy.ndarray] = None


def _nearest_indices(colors: numpy.ndarray) -> numpy.ndarray:
    """
    (N, 3) 的顏色找最近的調色盤索引。分批算：一次全算會產生 N x 256 x 3 的
    中間陣列，一張 1280x720 的畫面就要 3.8 GB。
    Nearest palette index for an (N, 3) array of colours, in chunks: doing it in
    one go materialises an N x 256 x 3 intermediate, which is 3.8 GB for a
    single 1280x720 frame.
    """
    result = numpy.empty(colors.shape[0], dtype=numpy.uint8)
    palette = _PALETTE_ARRAY.reshape((1, -1, 3))
    for start in range(0, colors.shape[0], _LOOKUP_CHUNK):
        chunk = colors[start:start + _LOOKUP_CHUNK].reshape((-1, 1, 3))
        distances = ((chunk - palette) ** 2).sum(axis=2)
        result[start:start + _LOOKUP_CHUNK] = distances.argmin(axis=1).astype(numpy.uint8)
    return result


def _get_lookup_table() -> numpy.ndarray:
    """
    32x32x32 的最近色查表，第一次用到才建（約 33k 次搜尋，之後每張畫面只要
    三次位移加一次索引）。調色盤是固定的，所以這張表也是固定的。
    A 32x32x32 nearest-colour table, built on first use (~33k searches; after
    that a frame costs three shifts and one indexing operation). The palette is
    fixed, so the table is too.
    """
    global _lookup_table
    if _lookup_table is None:
        centers = numpy.arange(_LOOKUP_STEPS, dtype=numpy.int32) * (1 << _LOOKUP_BITS) \
            + (1 << (_LOOKUP_BITS - 1))
        grid = numpy.stack(
            numpy.meshgrid(centers, centers, centers, indexing="ij"), axis=-1)
        _lookup_table = _nearest_indices(grid.reshape((-1, 3))).reshape(
            (_LOOKUP_STEPS, _LOOKUP_STEPS, _LOOKUP_STEPS))
    return _lookup_table


def quantize(pixels: numpy.ndarray) -> numpy.ndarray:
    """
    把 H x W x 3 的畫面對應到調色盤索引（最近色）。
    Map an H x W x 3 frame onto palette indices by nearest colour.
    """
    data = numpy.asarray(pixels, dtype=numpy.int32)
    if data.ndim != 3 or data.shape[2] < 3:
        raise ValueError("frame must be H x W x 3")
    table = _get_lookup_table()
    binned = data[:, :, :3] >> _LOOKUP_BITS
    return table[binned[:, :, 0], binned[:, :, 1], binned[:, :, 2]]


def clamp_delay(delay_ms) -> int:
    """GIF 的延遲以 1/100 秒為單位，太短的值瀏覽器與看圖程式會自己改掉。"""
    try:
        value = int(delay_ms)
    except (TypeError, ValueError):
        value = 100
    return max(MIN_DELAY_MS, value)


def lzw_encode(indices: Sequence[int], min_code_size: int = _MIN_CODE_SIZE) -> bytes:
    """
    GIF 用的 LZW 壓縮（可變碼長，字典滿了就送 clear code 重來）。
    The LZW variant GIF uses: variable code width, reset on a full dictionary.
    """
    dictionary = {bytes([value]): value for value in range(_CLEAR_CODE)}
    next_code = _END_CODE + 1
    code_size = min_code_size + 1
    output = _BitWriter()
    output.write(_CLEAR_CODE, code_size)
    current = b""
    for value in indices:
        candidate = current + bytes([value])
        if candidate in dictionary:
            current = candidate
            continue
        output.write(dictionary[current], code_size)
        dictionary[candidate] = next_code
        next_code += 1
        if next_code > (1 << code_size):
            if code_size < 12:
                code_size += 1
            else:
                output.write(_CLEAR_CODE, code_size)
                dictionary = {bytes([v]): v for v in range(_CLEAR_CODE)}
                next_code = _END_CODE + 1
                code_size = min_code_size + 1
        current = bytes([value])
    if current:
        output.write(dictionary[current], code_size)
    output.write(_END_CODE, code_size)
    return output.finish()


class _BitWriter:
    """把不定長度的碼一位一位塞進位元組串（GIF 是低位先出）。"""

    def __init__(self) -> None:
        self._bits = 0
        self._count = 0
        self._data = bytearray()

    def write(self, code: int, width: int) -> None:
        self._bits |= (int(code) & ((1 << width) - 1)) << self._count
        self._count += width
        while self._count >= 8:
            self._data.append(self._bits & 0xFF)
            self._bits >>= 8
            self._count -= 8

    def finish(self) -> bytes:
        if self._count > 0:
            self._data.append(self._bits & 0xFF)
            self._bits = 0
            self._count = 0
        return bytes(self._data)


def _blocks(data: bytes) -> bytes:
    """把壓縮後的資料切成 GIF 要求的 255 位元組區塊。"""
    out = bytearray()
    for start in range(0, len(data), 255):
        chunk = data[start:start + 255]
        out.append(len(chunk))
        out.extend(chunk)
    out.append(0)
    return bytes(out)


def _screen_descriptor(width: int, height: int) -> bytes:
    # 全域調色盤、每色 8 位元、256 色
    # Global colour table, 8 bits per colour, 256 entries.
    return (width.to_bytes(2, "little") + height.to_bytes(2, "little")
            + bytes([0xF7, 0, 0])
            + b"".join(bytes(color) for color in _PALETTE))


def _graphic_control(delay_ms: int) -> bytes:
    delay = clamp_delay(delay_ms) // 10
    return b"\x21\xf9\x04\x04" + delay.to_bytes(2, "little") + b"\x00\x00"


def _image_descriptor(width: int, height: int) -> bytes:
    return b"\x2c" + (0).to_bytes(2, "little") + (0).to_bytes(2, "little") \
        + width.to_bytes(2, "little") + height.to_bytes(2, "little") + b"\x00"


def _loop_extension() -> bytes:
    """NETSCAPE 擴充：讓動畫無限循環。"""
    return b"\x21\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00"


def encode_gif(frames: Iterable[numpy.ndarray], delay_ms: int = 100,
               loop: bool = True) -> Optional[bytes]:
    """
    把一連串 H x W x 3 的畫面編成動畫 GIF；沒有畫面時回傳 None。
    尺寸以第一張為準，之後大小不同的畫面會被略過（不會畫錯位）。
    Encode frames into an animated GIF, or None when there are none. The first
    frame sets the size; later frames of a different size are skipped rather
    than drawn misaligned.
    """
    stream = BytesIO()
    width = height = 0
    written = 0
    for frame in frames:
        data = numpy.asarray(frame)
        if data.ndim != 3 or data.shape[2] < 3:
            continue
        if width == 0:
            height, width = int(data.shape[0]), int(data.shape[1])
            stream.write(_HEADER + _screen_descriptor(width, height))
            if loop:
                stream.write(_loop_extension())
        elif data.shape[0] != height or data.shape[1] != width:
            continue
        _write_frame(stream, data, delay_ms)
        written += 1
    if written == 0:
        return None
    stream.write(_TRAILER)
    return stream.getvalue()


def _write_frame(stream, data: numpy.ndarray, delay_ms: int) -> int:
    """Write one image block; return its seekable delay field offset."""
    height, width = data.shape[:2]
    delay_offset = stream.tell() + 4
    stream.write(_graphic_control(delay_ms))
    stream.write(_image_descriptor(width, height))
    stream.write(bytes([_MIN_CODE_SIZE]))
    compressed = lzw_encode(quantize(data).reshape(-1))
    for start in range(0, len(compressed), 255):
        chunk = compressed[start:start + 255]
        stream.write(bytes([len(chunk)]))
        stream.write(chunk)
    stream.write(b"\x00")
    return delay_offset


class IncrementalGifWriter:
    """Flush each frame to a sibling temporary file, then atomically publish it."""

    def __init__(self, target: str | Path, delay_ms: int = 100) -> None:
        self.target = Path(target)
        self.target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(prefix=f".{self.target.name}.",
                                           suffix=".part", dir=self.target.parent)
        self.temp_path = Path(name)
        self._stream = os.fdopen(descriptor, "w+b")
        self._delay_ms = delay_ms
        self.frame_count = 0
        self._shape = None
        self._previous_timestamp = None
        self._delay_offset = None
        self._result = None
        self._cancel_requested = threading.Event()

    def _patch_delay(self, timestamp: float | None) -> None:
        if timestamp is None or self._delay_offset is None:
            return
        delay_ms = round((timestamp - self._previous_timestamp) * 1000)
        position = self._stream.tell()
        self._stream.seek(self._delay_offset)
        self._stream.write((clamp_delay(delay_ms) // 10).to_bytes(2, "little"))
        self._stream.seek(position)

    def append(self, frame: numpy.ndarray, timestamp: float | None = None) -> None:
        if self._stream.closed:
            raise RuntimeError("GIF writer is closed")
        data = numpy.asarray(frame)
        if data.ndim != 3 or data.shape[2] != 3 or data.dtype != numpy.uint8:
            raise ValueError("frame must be an H x W x 3 uint8 array")
        height, width = data.shape[:2]
        if not (0 < width <= 65535 and 0 < height <= 65535):
            raise ValueError("GIF dimensions must be between 1 and 65535")
        if self._shape is not None and self._shape != data.shape:
            raise ValueError("recording frame size changed")
        timestamp = time.monotonic() if timestamp is None else timestamp
        if self._shape is None:
            self._stream.write(_HEADER + _screen_descriptor(width, height) + _loop_extension())
            self._shape = data.shape
        self._patch_delay(timestamp)
        self._delay_offset = _write_frame(self._stream, data, self._delay_ms)
        self._previous_timestamp = timestamp
        self.frame_count += 1
        self._stream.flush()

    def finish(self, timestamp: float | None = None) -> Optional[str]:
        if self._stream.closed:
            return self._result
        if not self.frame_count:
            self.cancel()
            return None
        try:
            self._patch_delay(timestamp)
            self._stream.write(_TRAILER)
            self._stream.flush()
            os.fsync(self._stream.fileno())
            self._stream.close()
            if self._cancel_requested.is_set():
                self.cancel()
                return None
            os.replace(self.temp_path, self.target)
            self._result = str(self.target)
            return self._result
        except Exception:
            self.cancel()
            raise

    def cancel(self) -> None:
        try:
            self._stream.close()
        finally:
            self.temp_path.unlink(missing_ok=True)


MAX_QUEUED_FRAMES = 3
MAX_QUEUED_BYTES = 64 * 1024 * 1024


class AsyncGifWriter:
    """Own the file on a worker thread; never wait for encoding on the GUI thread."""

    def __init__(self, target: str | Path, delay_ms: int = 100,
                 callback: Optional[Callable] = None,
                 writer_factory: Callable = IncrementalGifWriter,
                 max_frames: int = MAX_QUEUED_FRAMES,
                 max_bytes: int = MAX_QUEUED_BYTES) -> None:
        self._condition = threading.Condition()
        self._queue = deque()
        self._bytes = 0
        self._max_frames, self._max_bytes = max_frames, max_bytes
        self._stopping = self._cancelled = False
        self._end_timestamp = None
        self._callback = callback
        self._done = threading.Event()
        self._cancel_requested = threading.Event()
        self.error = None
        self.result = None
        self.temp_path = None
        self._thread = threading.Thread(target=self._run,
                                        args=(target, delay_ms, writer_factory), daemon=True)
        self._thread.start()

    @property
    def done(self) -> bool:
        return self._done.is_set()

    @property
    def queued_frames(self) -> int:
        with self._condition:
            return len(self._queue)

    @property
    def queued_bytes(self) -> int:
        with self._condition:
            return self._bytes

    def can_accept(self, size: int) -> bool:
        with self._condition:
            return (not self._stopping and not self.done
                    and len(self._queue) < self._max_frames
                    and self._bytes + size <= self._max_bytes)

    def submit(self, pixels: numpy.ndarray, timestamp: float) -> bool:
        """Transfer ownership of a copied RGB frame; False means it was dropped."""
        with self._condition:
            if not self.can_accept(pixels.nbytes):
                return False
            self._queue.append((pixels, timestamp))
            self._bytes += pixels.nbytes
            self._condition.notify()
            return True

    def stop(self, timestamp: float | None = None) -> None:
        with self._condition:
            if not self._stopping:
                self._stopping = True
                self._end_timestamp = timestamp
            self._condition.notify()

    def cancel(self) -> None:
        self._cancel_requested.set()
        with self._condition:
            self._cancelled = self._stopping = True
            self._queue.clear()
            self._bytes = 0
            self._condition.notify()

    def _drain(self, writer: IncrementalGifWriter) -> None:
        while True:
            with self._condition:
                self._condition.wait_for(lambda: self._queue or self._stopping)
                if self._cancelled:
                    return
                if not self._queue:
                    break
                pixels, timestamp = self._queue.popleft()
                self._bytes -= pixels.nbytes
            writer.append(pixels, timestamp)
        if not self._cancel_requested.is_set():
            self.result = writer.finish(self._end_timestamp)

    def _run(self, target, delay_ms, factory) -> None:
        writer = None
        try:
            writer = factory(target, delay_ms=delay_ms)
            writer._cancel_requested = self._cancel_requested
            self.temp_path = writer.temp_path
            self._drain(writer)
        except Exception as error:
            self.error = str(error)
        finally:
            if writer is not None and self.result is None:
                try:
                    writer.cancel()
                except OSError as error:
                    self.error = self.error or str(error)
            with self._condition:
                self._queue.clear()
                self._bytes = 0
                self._stopping = True
            self._done.set()
            if self._callback is not None:
                self._callback(self, self.result, self.error)
