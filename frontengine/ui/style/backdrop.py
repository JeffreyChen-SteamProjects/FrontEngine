"""
What the glass lies on: the desktop wallpaper, blurred, or a built-in dusk / dawn.

The window is opaque and paints this itself. Asking the system for a see-through
window instead is what turned full-screen layers black on some GPUs, and a blurred
copy of the wallpaper is what the system's own material shows anyway.

The wallpaper is read from this computer, decoded at a tiny size and kept in memory
only. It is pulled towards the theme's tint far enough that text stays readable over
any picture (``BACKDROP_MIX``; ``test_glass_interface.py`` checks the extremes).
"""
from __future__ import annotations

import os
import stat
import sys
from pathlib import Path
from typing import Callable, Optional, Tuple

import numpy
from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QImage, QImageReader, QPainter, QPixmap

from frontengine.ui.style.tokens import BACKDROP_MIX, palette_for
from frontengine.utils.logging.loggin_instance import front_engine_logger

SAMPLE = QSize(64, 36)           # what is kept of the wallpaper: enough for colour, not for detail
RENDERED = QSize(480, 270)       # blurred and stored; scaled smoothly to the window
BLUR_RADIUS = 34
SATURATION = 1.45                # blurring greys colours out; this puts them back
DARK_CEILING, LIGHT_FLOOR = 94.0, 180.0        # the brightness the wallpaper may reach in each theme
MAX_FILE_BYTES = 64 * 1024 * 1024
_DRIVE_REMOTE = 4
# Offline, or kept in the cloud until read (OneDrive): reading it would wait for a download.
_NOT_HERE = 0x00001000 | 0x00040000 | 0x00400000
_SPI_GETDESKWALLPAPER = 0x0073
_LUMA = numpy.array([.2126, .7152, .0722], dtype=numpy.float32)


def desktop_wallpaper() -> Optional[Path]:
    """The current wallpaper's file; None when there is none or the system is not asked for it."""
    if sys.platform != "win32":
        return None
    try:  # pragma: no cover - Win32 boundary
        import ctypes
        buffer = ctypes.create_unicode_buffer(1024)
        user32 = ctypes.WinDLL("user32")
        if not user32.SystemParametersInfoW(_SPI_GETDESKWALLPAPER, len(buffer), buffer, 0) or not buffer.value:
            return None
        return Path(buffer.value)
    except (OSError, ValueError) as error:  # pragma: no cover
        front_engine_logger.debug(f"[Backdrop] wallpaper unknown: {error!r}")
        return None


def is_remote(path: Path) -> bool:
    """On a network share or drive, where even asking about the file can wait for seconds."""
    if str(path).startswith(("\\\\", "//")):
        return True
    if sys.platform != "win32" or not path.drive:
        return False
    try:  # pragma: no cover - Win32 boundary
        import ctypes
        return ctypes.WinDLL("kernel32").GetDriveTypeW(path.drive + "\\") == _DRIVE_REMOTE
    except OSError:  # pragma: no cover
        return False


def local_wallpaper(path: Optional[Path]) -> Optional[Path]:
    """The wallpaper where it can be read at once: Windows keeps its own copy of a remote one."""
    if path is None or not is_remote(path):
        return path
    roaming = os.environ.get("APPDATA")
    return Path(roaming) / "Microsoft" / "Windows" / "Themes" / "TranscodedWallpaper" if roaming else None


def _stamp(path: Optional[Path]) -> Optional[tuple]:
    """What identifies this picture, or None when it cannot be used."""
    if path is None:
        return None
    try:
        status = path.stat()
        if not stat.S_ISREG(status.st_mode) or not 0 < status.st_size <= MAX_FILE_BYTES:
            return None
        if getattr(status, "st_file_attributes", 0) & _NOT_HERE:
            return None
    except OSError:
        return None
    return str(path), status.st_mtime_ns, status.st_size


def _sample(path: Path) -> Optional[numpy.ndarray]:
    """The picture cropped to the sample's shape and shrunk, as H x W x 3 floats; None if unreadable."""
    reader = QImageReader(str(path))
    reader.setDecideFormatFromContent(True)
    reader.setAutoTransform(True)
    size = reader.size()
    if size.isValid():
        reader.setScaledSize(size.scaled(SAMPLE * 2, Qt.AspectRatioMode.KeepAspectRatioByExpanding))
    image = reader.read()
    if image.isNull():
        return None
    image = image.scaled(SAMPLE, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                         Qt.TransformationMode.SmoothTransformation)
    left, top = (image.width() - SAMPLE.width()) // 2, (image.height() - SAMPLE.height()) // 2
    return _to_array(image.copy(QRect(left, top, SAMPLE.width(), SAMPLE.height())))


def _to_array(image: QImage) -> numpy.ndarray:
    image = image.convertToFormat(QImage.Format.Format_RGB888)
    raw = numpy.frombuffer(image.constBits(), dtype=numpy.uint8, count=image.bytesPerLine() * image.height())
    rows = raw.reshape((image.height(), image.bytesPerLine()))[:, : image.width() * 3]
    return rows.reshape((image.height(), image.width(), 3)).astype(numpy.float32)


def _to_image(pixels: numpy.ndarray) -> QImage:
    data = numpy.ascontiguousarray(numpy.clip(pixels + .5, 0, 255), dtype=numpy.uint8)
    height, width = data.shape[:2]
    return QImage(data.tobytes(), width, height, width * 3, QImage.Format.Format_RGB888).copy()


def _rgb(color: str) -> numpy.ndarray:
    value = QColor(color)
    return numpy.array([value.red(), value.green(), value.blue()], dtype=numpy.float32)


def _blur(pixels: numpy.ndarray, radius: int) -> numpy.ndarray:
    """Three box blurs along each axis: close to a Gaussian, edges repeated."""
    for _pass in range(3):
        for axis in (0, 1):
            reach = min(radius, pixels.shape[axis] // 3)
            pad = [(0, 0)] * 3
            pad[axis] = (reach + 1, reach)
            total = numpy.cumsum(numpy.pad(pixels, pad, mode="edge"), axis=axis, dtype=numpy.float64)
            length = total.shape[axis]
            high = numpy.take(total, numpy.arange(2 * reach + 1, length), axis=axis)
            low = numpy.take(total, numpy.arange(0, length - 2 * reach - 1), axis=axis)
            pixels = ((high - low) / (2 * reach + 1)).astype(numpy.float32)
    return pixels


def tinted(pixels: numpy.ndarray, tone: str) -> numpy.ndarray:
    """Pulled towards the theme's tint, so the same text reads over any wallpaper."""
    grey = (pixels @ _LUMA)[..., None]
    vivid = numpy.clip(grey + (pixels - grey) * SATURATION, 0, 255)
    bright = (vivid @ _LUMA)[..., None]
    if tone == "dark":                   # a bright wallpaper is dimmed, a dark one lifted, keeping its hue
        vivid = vivid * numpy.minimum(1, DARK_CEILING / numpy.maximum(bright, 1))
    else:
        vivid = 255 - (255 - vivid) * numpy.minimum(1, (255 - LIGHT_FLOOR) / numpy.maximum(255 - bright, 1))
    mix = BACKDROP_MIX[tone]
    return _rgb(palette_for(tone)["backdrop"]) * (1 - mix) + vivid * mix


def built_in(tone: str) -> numpy.ndarray:
    """Dusk over the sea, or dawn: soft glows on the theme's tint."""
    colors = palette_for(tone)
    height, width = RENDERED.height(), RENDERED.width()
    ys, xs = numpy.mgrid[0:height, 0:width].astype(numpy.float32)
    pixels = numpy.broadcast_to(_rgb(colors["backdrop"]), (height, width, 3)).copy()
    for name, (x, y, reach_x, reach_y), strength in (
            ("glow_cool", (.10, .02, .62, .75), .95), ("glow_mid", (.60, .42, .70, .70), .75),
            ("glow_warm", (.82, 1.06, .62, .55), .55)):
        distance = numpy.hypot((xs / width - x) / reach_x, (ys / height - y) / reach_y)
        weight = numpy.clip(1 - distance, 0, 1) ** 1.4 * strength
        pixels += (_rgb(colors[name]) - pixels) * weight[..., None]
    return pixels


class Backdrop:
    """Renders and caches the picture behind one window."""

    def __init__(self, wallpaper: Optional[Callable[[], Optional[Path]]] = None) -> None:
        self._wallpaper = wallpaper or (lambda: desktop_wallpaper())
        self._sampled: Tuple[Optional[tuple], Optional[numpy.ndarray]] = (None, None)
        self._image: Optional[QImage] = None
        self._image_key: Optional[tuple] = None
        self._pixmap: Optional[QPixmap] = None
        self._pixmap_key: Optional[tuple] = None
        self._stamp: Optional[tuple] = None
        self.use_wallpaper = True

    @property
    def shows_wallpaper(self) -> bool:
        return self._stamp is not None

    def refresh(self) -> bool:
        """Look whether the wallpaper changed; True when the picture has to be painted again."""
        stamp = None
        if self.use_wallpaper:
            path = local_wallpaper(self._wallpaper())
            stamp = _stamp(path)
            if stamp is not None and stamp != self._sampled[0]:
                self._sampled = (stamp, _sample(path))
            if stamp is not None and self._sampled[1] is None:
                stamp = None                             # a file Qt cannot read
        changed = stamp != self._stamp
        self._stamp = stamp
        return changed

    def set_use_wallpaper(self, use: bool) -> bool:
        self.use_wallpaper = bool(use)
        return self.refresh()

    def image(self, tone: str) -> QImage:
        key = (tone, self._stamp)
        if self._image is None or key != self._image_key:
            self._image, self._image_key = self._render(tone), key
        return self._image

    def _render(self, tone: str) -> QImage:
        if self._stamp is None:
            return _to_image(built_in(tone))
        small = _to_image(self._sampled[1])
        large = _to_array(small.scaled(RENDERED, Qt.AspectRatioMode.IgnoreAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation))
        return _to_image(tinted(_blur(large, BLUR_RADIUS), tone))

    def paint(self, painter: QPainter, rect: QRect, tone: str, ratio: float) -> None:
        """Fill ``rect`` (a whole window) with the picture."""
        size = QSize(max(1, round(rect.width() * ratio)), max(1, round(rect.height() * ratio)))
        key = (tone, self._stamp, size.width(), size.height())
        if self._pixmap is None or key != self._pixmap_key:
            self._pixmap = QPixmap.fromImage(self.image(tone).scaled(
                size, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self._pixmap.setDevicePixelRatio(ratio)
            self._pixmap_key = key
        painter.drawPixmap(rect.topLeft(), self._pixmap)
