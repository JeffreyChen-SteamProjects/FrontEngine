from dataclasses import dataclass, field
import math

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QImage, QPainter, QTransform


@dataclass
class Layer:
    key: str
    image: QImage
    transform: QTransform = field(default_factory=QTransform)
    z: float = 0.0
    opacity: float = 1.0
    # Clip is in output logical coordinates, before the layer transform.
    clip: QRectF | None = None


def compose_frame(layers: list[Layer], size: QSize, dpr: float = 1.0) -> QImage:
    if not math.isfinite(dpr) or dpr <= 0:
        raise ValueError('device pixel ratio must be positive')
    image = QImage(max(1, round(size.width() * dpr)), max(1, round(size.height() * dpr)),
                   QImage.Format.Format_RGBA8888_Premultiplied)
    image.setDevicePixelRatio(dpr)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    for layer in sorted(layers, key=lambda item: item.z):
        painter.save()
        if layer.clip is not None:
            painter.setClipRect(layer.clip)
        painter.setWorldTransform(layer.transform)
        painter.setOpacity(max(0.0, min(1.0, layer.opacity)))
        painter.drawImage(0, 0, layer.image)
        painter.restore()
    painter.end()
    return image
