"""A real OpenGL texture compositor with a visible software fallback."""
from PySide6.QtCore import Qt, Signal, QTimer, QRectF
from PySide6.QtGui import QGuiApplication, QPainter, QImage, QTransform
from PySide6.QtWidgets import QWidget

from .layers import compose_frame


class CompositorWidget(QWidget):
    backend_changed = Signal(str, str)

    def __init__(self, parent=None, backend: str = 'auto') -> None:
        super().__init__(parent)
        if backend not in ('auto', 'gpu', 'software'):
            raise ValueError('backend must be auto, gpu or software')
        self.layers = []
        self.actual_backend = 'software'
        self.failure_reason = ''
        self._gl = None
        self._layer_signature = None
        self._frame_signature = None
        self._cached_frame = QImage()
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        if backend != 'software':
            if QGuiApplication.platformName() in ('offscreen', 'minimal'):
                self.failure_reason = 'Qt platform has no OpenGL widget support'
            else:
                from .gl_widget import GLCompositor
                self._gl = GLCompositor(self)
                self._gl.failed.connect(self._fallback)
                self._gl.ready.connect(self._ready)
                self._gl.show()

    def _ready(self) -> None:
        self.actual_backend = 'gpu'
        self.failure_reason = ''
        self.backend_changed.emit('gpu', '')

    def _fallback(self, reason: str) -> None:
        self.failure_reason = reason
        self.actual_backend = 'software'
        if self._gl is not None:
            self._gl.hide()
            QTimer.singleShot(0, self._gl, self._gl.cleanup)
        self.backend_changed.emit('software', reason)
        self.update()

    def _probe_gpu(self) -> None:
        if self._gl is not None and not self._gl.isValid():
            self._fallback('OpenGL context could not be created')

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._gl is not None:
            QTimer.singleShot(250, self, self._probe_gpu)

    def set_layers(self, layers) -> None:
        self.layers = list(layers)
        signature = self._signature()
        if signature == self._layer_signature:
            return
        self._layer_signature = signature
        if self._gl is not None:
            self._gl.layers = self.layers
            self._gl.update()
        self.update()

    def output_frame(self):
        if self.actual_backend == 'gpu' and self._gl is not None:
            return self._gl.grabFramebuffer()
        return self._software_frame()

    def _signature(self) -> tuple:
        return tuple((layer.key, layer.image.cacheKey(), layer.image.devicePixelRatio(),
                      QTransform(layer.transform), layer.z, layer.opacity,
                      QRectF(layer.clip) if layer.clip is not None else None) for layer in self.layers)

    def _software_frame(self) -> QImage:
        """Reuse unchanged composition; returned shallow copies isolate caller mutations."""
        signature = (self.width(), self.height(), self.devicePixelRatioF(), self._signature())
        if self.width() * self.height() * self.devicePixelRatioF() ** 2 > 16_777_216:
            self._cached_frame = QImage()
            self._frame_signature = None
            return compose_frame(self.layers, self.size(), self.devicePixelRatioF())
        if self._frame_signature != signature:
            self._cached_frame = compose_frame(self.layers, self.size(), self.devicePixelRatioF())
            self._frame_signature = signature
        return QImage(self._cached_frame)

    def resizeEvent(self, event) -> None:
        if self._gl is not None:
            self._gl.setGeometry(self.rect())
        super().resizeEvent(event)

    def paintEvent(self, event) -> None:
        if self.actual_backend == 'software':
            painter = QPainter(self)
            painter.drawImage(0, 0, self._software_frame())

    def shutdown(self) -> None:
        if self._gl is not None:
            self._gl.cleanup()
        self.layers.clear()
        self._cached_frame = QImage()
        self._layer_signature = self._frame_signature = None

    def closeEvent(self, event) -> None:
        self.shutdown()
        super().closeEvent(event)
