"""Incremental silent MJPEG AVI with on-disk index and atomic publication.

Container layout follows Microsoft's AVI RIFF File Reference. JPEG encoding
uses Qt's existing image plugin; no external executable or codec is launched.
"""
from __future__ import annotations

import math
import os
from pathlib import Path
import shutil
import struct
import tempfile
import threading
import time

import numpy
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QImage

MAX_AVI_BYTES = 2 * 1024 ** 3
MAX_AVI_SECONDS = 3600
MAX_AVI_FRAMES = MAX_AVI_SECONDS * 20


def _chunk(kind: bytes, data: bytes) -> bytes:
    return kind + struct.pack('<I', len(data)) + data + (b'\0' if len(data) % 2 else b'')


def _header(width: int, height: int, delay_ms: int, frames: int, largest: int) -> bytes:
    main = struct.pack('<14I', delay_ms * 1000, largest * 1000 // delay_ms, 0, 0x10,
                       frames, 0, 1, largest, width, height, 0, 0, 0, 0)
    stream = struct.pack('<4s4sIHH8I4h', b'vids', b'MJPG', 0, 0, 0, 0,
                         delay_ms, 1000, 0, frames, largest, 0xFFFFFFFF, 0, 0, 0, width, height)
    bitmap = struct.pack('<IiiHH4sIiiII', 40, width, height, 1, 24, b'MJPG',
                         width * height * 3, 0, 0, 0, 0)
    return b'RIFF\0\0\0\0AVI ' + _chunk(b'LIST', b'hdrl' + _chunk(b'avih', main) +
            _chunk(b'LIST', b'strl' + _chunk(b'strh', stream) + _chunk(b'strf', bitmap)))


def _jpeg(pixels: numpy.ndarray) -> bytes:
    height, width = pixels.shape[:2]
    image = QImage(pixels.data, width, height, pixels.strides[0], QImage.Format.Format_RGB888)
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    try:
        if not image.save(buffer, 'JPG', 85):
            raise ValueError('Qt JPEG encoder is unavailable')
        return bytes(buffer.data())
    finally:
        buffer.close()


class IncrementalAviWriter:
    """Hold one JPEG in memory; stream frames and index to bounded disk files."""

    def __init__(self, target: str | Path, delay_ms: int = 100) -> None:
        self.target = Path(target).resolve()
        self.delay_ms = max(50, min(1000, int(delay_ms)))
        self._cancel_requested = threading.Event()
        self._stream = tempfile.NamedTemporaryFile(mode='w+b', suffix='.part',
            prefix='.' + self.target.name + '.', dir=self.target.parent, delete=False)
        self.temp_path = Path(self._stream.name)
        try:
            self._index = tempfile.TemporaryFile(mode='w+b', dir=self.target.parent)
        except OSError:
            self.cancel()
            raise
        self._shape = None
        self._first_timestamp = None
        self._last_timestamp = None
        self._last_jpeg = None
        self._largest = 0
        self._movi_start = 0
        self.frame_count = 0
        self._result = None

    def append(self, pixels: numpy.ndarray, timestamp: float | None = None) -> None:
        """Encode a copied RGB frame and fill dropped-frame intervals on disk."""
        if self._stream.closed or self._cancel_requested.is_set():
            return
        data = numpy.ascontiguousarray(pixels)
        if data.dtype != numpy.uint8 or data.ndim != 3 or data.shape[2] != 3:
            raise ValueError('AVI frames must be RGB uint8 arrays')
        height, width = data.shape[:2]
        if not 0 < width <= 32767 or not 0 < height <= 32767 or data.nbytes > 64 * 1024 ** 2:
            raise ValueError('AVI frame exceeds supported dimensions or 64 MiB')
        if self._shape is not None and self._shape != data.shape:
            raise ValueError('Recording frame size changed')
        stamp = time.monotonic() if timestamp is None else timestamp
        self._validate_timestamp(stamp)
        if self._shape is None:
            self._shape, self._first_timestamp = data.shape, stamp
            self._stream.write(_header(width, height, self.delay_ms, 0, 0))
            self._movi_start = self._stream.tell()
            self._stream.write(b'LIST\0\0\0\0movi')
        slot = int((stamp - self._first_timestamp) * 1000 / self.delay_ms + 1e-6)
        self._fill_until(slot)
        encoded = _jpeg(data)
        if self.frame_count <= slot:
            self._write_jpeg(encoded)
        self._last_jpeg, self._last_timestamp = encoded, stamp
        self._stream.flush()

    def _validate_timestamp(self, stamp: float) -> None:
        if not isinstance(stamp, (int, float)) or not math.isfinite(stamp):
            raise ValueError('Recording timestamp must be finite')
        if self._last_timestamp is not None and stamp < self._last_timestamp:
            raise ValueError('Recording timestamps must not go backwards')
        if self._first_timestamp is not None and stamp - self._first_timestamp > MAX_AVI_SECONDS:
            raise ValueError('AVI recording exceeds one hour')

    def _fill_until(self, count: int) -> None:
        if count > MAX_AVI_FRAMES:
            raise ValueError('AVI recording exceeds the frame limit')
        while self.frame_count < count and self._last_jpeg is not None:
            if self._cancel_requested.is_set():
                return
            self._write_jpeg(self._last_jpeg)

    def _write_jpeg(self, encoded: bytes) -> None:
        projected = self._stream.tell() + len(encoded) + 10 + (self.frame_count + 1) * 16 + 8
        if projected > MAX_AVI_BYTES or self.frame_count >= MAX_AVI_FRAMES:
            raise ValueError('AVI recording exceeds the 2 GiB or frame limit')
        offset = self._stream.tell() - self._movi_start - 8
        self._stream.write(_chunk(b'00dc', encoded))
        self._index.write(struct.pack('<4sIII', b'00dc', 0x10, offset, len(encoded)))
        self._largest = max(self._largest, len(encoded))
        self.frame_count += 1

    def finish(self, timestamp: float | None = None) -> str | None:
        """Flush the on-disk index and publish only a complete, uncancelled AVI."""
        if self._stream.closed:
            return self._result
        if not self.frame_count or self._cancel_requested.is_set():
            self.cancel()
            return None
        try:
            if timestamp is not None:
                self._validate_timestamp(timestamp)
                count = max(1, math.ceil((timestamp - self._first_timestamp) * 1000 / self.delay_ms - 1e-6))
                self._fill_until(count)
            self._finalize()
            if self._cancel_requested.is_set():
                self.cancel()
                return None
            os.replace(self.temp_path, self.target)
            self._result = str(self.target)
            return self._result
        except (OSError, ValueError):
            self.cancel()
            raise

    def _finalize(self) -> None:
        movi_end = self._stream.tell()
        self._stream.write(b'idx1' + struct.pack('<I', self.frame_count * 16))
        self._index.seek(0)
        shutil.copyfileobj(self._index, self._stream, length=65536)
        end = self._stream.tell()
        height, width = self._shape[:2]
        self._stream.seek(0)
        self._stream.write(_header(width, height, self.delay_ms, self.frame_count, self._largest))
        self._stream.seek(4)
        self._stream.write(struct.pack('<I', end - 8))
        self._stream.seek(self._movi_start + 4)
        self._stream.write(struct.pack('<I', movi_end - self._movi_start - 8))
        self._stream.flush()
        os.fsync(self._stream.fileno())
        self._stream.close()
        self._index.close()
        self._last_jpeg = None

    def cancel(self) -> None:
        """Remove temporary output without touching an existing destination."""
        try:
            self._stream.close()
            if hasattr(self, '_index'):
                self._index.close()
        finally:
            self._last_jpeg = None
            self.temp_path.unlink(missing_ok=True)
