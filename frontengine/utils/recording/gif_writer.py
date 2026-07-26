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

from typing import Iterable, List, Optional, Sequence, Tuple

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


def quantize(pixels: numpy.ndarray) -> numpy.ndarray:
    """
    把 H x W x 3 的畫面對應到調色盤索引（最近色）。
    Map an H x W x 3 frame onto palette indices by nearest colour.
    """
    data = numpy.asarray(pixels, dtype=numpy.int32)
    if data.ndim != 3 or data.shape[2] < 3:
        raise ValueError("frame must be H x W x 3")
    flat = data[:, :, :3].reshape((-1, 1, 3))
    distances = ((flat - _PALETTE_ARRAY.reshape((1, -1, 3))) ** 2).sum(axis=2)
    return distances.argmin(axis=1).astype(numpy.uint8).reshape(
        (data.shape[0], data.shape[1]))


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
    stream = bytearray(_HEADER)
    width = height = 0
    written = 0
    for frame in frames:
        data = numpy.asarray(frame)
        if data.ndim != 3 or data.shape[2] < 3:
            continue
        if width == 0:
            height, width = int(data.shape[0]), int(data.shape[1])
            stream.extend(_screen_descriptor(width, height))
            if loop:
                stream.extend(_loop_extension())
        elif data.shape[0] != height or data.shape[1] != width:
            continue
        stream.extend(_graphic_control(delay_ms))
        stream.extend(_image_descriptor(width, height))
        stream.append(_MIN_CODE_SIZE)
        stream.extend(_blocks(lzw_encode(quantize(data).reshape(-1).tolist())))
        written += 1
    if written == 0:
        return None
    stream.extend(_TRAILER)
    return bytes(stream)
