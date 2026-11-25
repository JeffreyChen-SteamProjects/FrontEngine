"""
Reads one window's area of the Windows desktop into a numpy array.

GDI in physical pixels: the area comes from the window's own ``GetWindowRect``,
so mixed display scaling needs no conversion. It may run on a worker thread, and
the desktop picture leaves out every window excluded from capture (see
``screen_privacy.capture_affinity``). Windows only; ``open_source`` returns None
elsewhere.
"""
from __future__ import annotations

import sys
from typing import Optional

import numpy

from frontengine.utils.logging.loggin_instance import front_engine_logger

_SRCCOPY = 0x00CC0020
_BI_RGB = 0
_DIB_RGB_COLORS = 0


class GdiScreenSource:  # pragma: no cover - needs the real Windows desktop
    """Copies the desktop under one window, frame after frame, into one reused bitmap."""

    def __init__(self, hwnd: int) -> None:
        import ctypes
        from ctypes import wintypes

        class BitmapInfoHeader(ctypes.Structure):
            _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                        ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD),
                        ("biCompression", wintypes.DWORD), ("biSizeImage", wintypes.DWORD),
                        ("biXPelsPerMeter", wintypes.LONG), ("biYPelsPerMeter", wintypes.LONG),
                        ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]

        self._ctypes, self._wintypes, self._header_type = ctypes, wintypes, BitmapInfoHeader
        # Private handles: argtypes set here must not leak into other users of windll.
        self._user32 = ctypes.WinDLL("user32")
        self._gdi32 = ctypes.WinDLL("gdi32")
        self._declare()
        self._hwnd = wintypes.HWND(int(hwnd))
        self._screen = self._user32.GetDC(None)
        self._memory = self._gdi32.CreateCompatibleDC(self._screen)
        self._bitmap = None
        self._old = None
        self._size = (0, 0)
        self._bits = ctypes.c_void_p()

    def _declare(self) -> None:
        ctypes, wt = self._ctypes, self._wintypes
        handle = ctypes.c_void_p
        for library, name, result, arguments in (
                (self._user32, "GetDC", handle, [wt.HWND]),
                (self._user32, "ReleaseDC", ctypes.c_int, [wt.HWND, handle]),
                (self._user32, "GetWindowRect", wt.BOOL, [wt.HWND, ctypes.POINTER(wt.RECT)]),
                (self._gdi32, "CreateCompatibleDC", handle, [handle]),
                (self._gdi32, "CreateDIBSection", handle,
                 [handle, handle, wt.UINT, ctypes.POINTER(ctypes.c_void_p), handle, wt.DWORD]),
                (self._gdi32, "SelectObject", handle, [handle, handle]),
                (self._gdi32, "DeleteObject", wt.BOOL, [handle]),
                (self._gdi32, "DeleteDC", wt.BOOL, [handle]),
                (self._gdi32, "BitBlt", wt.BOOL,
                 [handle] + [ctypes.c_int] * 4 + [handle, ctypes.c_int, ctypes.c_int, wt.DWORD])):
            function = getattr(library, name)
            function.restype, function.argtypes = result, arguments

    def _resize(self, width: int, height: int) -> bool:
        if self._bitmap is not None and self._size == (width, height):
            return True
        self._drop_bitmap()
        header = self._header_type()
        header.biSize = self._ctypes.sizeof(header)
        header.biWidth, header.biHeight = width, -height        # top-down rows
        header.biPlanes, header.biBitCount, header.biCompression = 1, 32, _BI_RGB
        bitmap = self._gdi32.CreateDIBSection(self._memory, self._ctypes.byref(header), _DIB_RGB_COLORS,
                                              self._ctypes.byref(self._bits), None, 0)
        if not bitmap:
            return False
        self._bitmap, self._size = bitmap, (width, height)
        self._old = self._gdi32.SelectObject(self._memory, bitmap)
        return True

    def grab(self) -> Optional[numpy.ndarray]:
        """The area as an H x W x 4 BGRX copy, or None when it cannot be read."""
        rect = self._wintypes.RECT()
        if not self._user32.GetWindowRect(self._hwnd, self._ctypes.byref(rect)):
            return None
        width, height = rect.right - rect.left, rect.bottom - rect.top
        if width <= 0 or height <= 0 or not self._resize(width, height):
            return None
        if not self._gdi32.BitBlt(self._memory, 0, 0, width, height, self._screen,
                                  rect.left, rect.top, _SRCCOPY):
            return None
        count = width * height * 4
        buffer = (self._ctypes.c_ubyte * count).from_address(self._bits.value)
        return numpy.frombuffer(buffer, dtype=numpy.uint8).reshape((height, width, 4)).copy()

    def _drop_bitmap(self) -> None:
        if self._bitmap is not None:
            self._gdi32.SelectObject(self._memory, self._old)
            self._gdi32.DeleteObject(self._bitmap)
            self._bitmap = None

    def close(self) -> None:
        """Release the bitmap and device contexts (on the thread that grabbed)."""
        self._drop_bitmap()
        if self._memory:
            self._gdi32.DeleteDC(self._memory)
            self._memory = None
        if self._screen:
            self._user32.ReleaseDC(None, self._screen)
            self._screen = None


def open_source(hwnd: int) -> Optional[GdiScreenSource]:
    """A source for the desktop under ``hwnd``; None where this is not available."""
    if sys.platform != "win32" or not hwnd:
        return None
    try:
        return GdiScreenSource(hwnd)
    except (OSError, AttributeError) as error:  # pragma: no cover - Win32 boundary
        front_engine_logger.warning(f"[ScreenSource] unavailable: {error!r}")
        return None
