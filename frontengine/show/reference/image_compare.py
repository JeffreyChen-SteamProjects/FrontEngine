"""Bounded image alignment and pixel differences on an explicit white backdrop."""
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QImageReader, QPainter

MAX_PIXELS = 16777216
MAX_DIMENSION = 8192
MAX_FILE_BYTES = 64 * 1024 * 1024


def checked_image(path: str) -> QImage:
    """Read the first frame only, honoring orientation and checking size first."""
    source = Path(path)
    if not source.is_file() or source.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("Choose an image file smaller than 64 MiB")
    reader = QImageReader(str(source))
    reader.setAutoTransform(True)
    size = reader.size()
    if (not size.isValid() or max(size.width(), size.height()) > MAX_DIMENSION
            or size.width() * size.height() > MAX_PIXELS):
        raise ValueError("Image dimensions exceed the comparison limit")
    image = reader.read()
    if image.isNull():
        raise ValueError("Image cannot be decoded: " + reader.errorString())
    return image.convertToFormat(QImage.Format.Format_RGBA8888)


def align_images(first: QImage, second: QImage, alignment: str) -> tuple[QImage, QImage]:
    """Use unscaled top-left/center alignment or fit B inside A with aspect preserved."""
    if first.isNull() or second.isNull() or alignment not in ('origin', 'center', 'fit'):
        raise ValueError("Invalid comparison images or alignment")
    if alignment == 'fit':
        width, height = first.width(), first.height()
        second = second.scaled(first.size(), Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
    else:
        width, height = max(first.width(), second.width()), max(first.height(), second.height())
    if max(width, height) > MAX_DIMENSION or width * height > MAX_PIXELS:
        raise ValueError("Aligned canvas exceeds the comparison limit")
    aligned = []
    for image in (first, second):
        canvas = QImage(width, height, QImage.Format.Format_RGBA8888)
        canvas.fill(Qt.GlobalColor.transparent)
        x, y = (0, 0) if alignment == 'origin' else ((width - image.width()) // 2,
                                                  (height - image.height()) // 2)
        painter = QPainter(canvas)
        painter.drawImage(x, y, image)
        painter.end()
        aligned.append(canvas)
    return aligned[0], aligned[1]


def _flatten(image: QImage) -> QImage:
    canvas = QImage(image.size(), QImage.Format.Format_RGBA8888)
    canvas.fill(QColor('white'))
    painter = QPainter(canvas)
    painter.drawImage(0, 0, image)
    painter.end()
    return canvas


def difference_image(first: QImage, second: QImage) -> QImage:
    """Return exact absolute RGB channel differences after alpha-over-white compositing."""
    if first.size() != second.size() or first.isNull():
        raise ValueError("Difference images must have the same non-empty size")
    if first.width() * first.height() > MAX_PIXELS:
        raise ValueError("Difference canvas exceeds the comparison limit")
    first, second = _flatten(first), _flatten(second)
    shape = (first.height(), first.width(), 4)
    a = np.frombuffer(first.constBits(), dtype=np.uint8).reshape(shape)
    b = np.frombuffer(second.constBits(), dtype=np.uint8).reshape(shape)
    output = np.empty(shape, dtype=np.uint8)
    output[:, :, :3] = np.abs(a[:, :, :3].astype(np.int16) - b[:, :, :3].astype(np.int16))
    output[:, :, 3] = 255
    return QImage(output.data, first.width(), first.height(), first.width() * 4,
                  QImage.Format.Format_RGBA8888).copy()
