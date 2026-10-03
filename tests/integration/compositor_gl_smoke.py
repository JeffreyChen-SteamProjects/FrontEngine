"""Run via runpy with the repository on sys.path and a real Qt desktop platform.

This deliberately does not import pytest/conftest or silently accept software fallback.
It opens and closes its own tiny window; it does not interact with existing windows.
"""
import json
import os
import statistics
import time

from PySide6.QtCore import QRectF, QSize
from PySide6.QtGui import QColor, QImage, QTransform
from PySide6.QtWidgets import QApplication

from frontengine.show.compositor import CompositorWidget, Layer, compose_frame


def main() -> None:
    application = QApplication.instance() or QApplication([])
    if application.platformName() in ('offscreen', 'minimal'):
        raise RuntimeError('Real desktop OpenGL is required; unset QT_QPA_PLATFORM')
    widget = CompositorWidget(backend='gpu')
    widget.resize(96, 64)
    layers = []
    for name, color, x, alpha, z in (('red', 'red', 0, 1, 0), ('blue', 'blue', 16, .5, 1)):
        image = QImage(64, 64, QImage.Format.Format_RGBA8888_Premultiplied)
        image.fill(QColor(color))
        layers.append(Layer(name, image, QTransform.fromTranslate(x, 0), z, alpha,
                            QRectF(24, 0, 16, 64) if name == 'blue' else None))
    widget.set_layers(layers)
    widget.show()
    try:
        for _ in range(20):
            application.processEvents()
        if widget.actual_backend != 'gpu':
            raise RuntimeError(widget.failure_reason or 'GPU context did not initialize')
        frame = widget.output_frame()
        expected = compose_frame(layers, QSize(96, 64), widget.devicePixelRatioF())
        ratio = widget.devicePixelRatioF()
        for x, y in ((8, 8), (26, 8), (42, 8), (80, 8)):
            actual, reference = frame.pixelColor(round(x * ratio), round(y * ratio)), expected.pixelColor(round(x * ratio), round(y * ratio))
            assert max(abs(a - b) for a, b in zip(actual.getRgb(), reference.getRgb())) <= 2, (x, actual, reference)
        timing = {}
        for backend in ('gpu', 'software'):
            durations = []
            for _ in range(30):
                started = time.perf_counter()
                if backend == 'gpu':
                    widget.output_frame()
                else:
                    compose_frame(layers, widget.size(), ratio)
                durations.append((time.perf_counter() - started) * 1000)
            timing[backend + '_frame_readback_ms'] = round(statistics.mean(durations), 3)
        print(json.dumps({'platform': application.platformName(), 'dpr': ratio,
                          'backend': widget.actual_backend, **timing}))
    finally:
        widget.shutdown()
        widget.close()
        application.processEvents()


if __name__ == '__main__':
    os.environ.pop('QT_QPA_PLATFORM', None)
    main()
