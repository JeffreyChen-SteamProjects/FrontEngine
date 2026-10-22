"""One zoomable view with aligned side-by-side, overlay, wipe and difference modes."""
from pathlib import Path
from threading import Event

from PySide6.QtCore import QObject, QRunnable, QRectF, Qt, QThreadPool, Signal
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QGraphicsPixmapItem, QGraphicsScene,
    QGraphicsView, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout,
)

from frontengine.show.reference.image_compare import align_images, checked_image, difference_image
from frontengine.utils.multi_language.retranslate import retranslator, tr, translate

_POOL = None


def comparison_pool() -> QThreadPool:
    """Bound concurrent decoding across closing/reopened comparison windows."""
    global _POOL
    if _POOL is None:
        _POOL = QThreadPool()
        _POOL.setMaxThreadCount(2)
    return _POOL


class _CompareSignals(QObject):
    finished = Signal(object, object, str)


class _CompareJob(QRunnable):
    def __init__(self, request, cancelled: Event) -> None:
        super().__init__()
        self.request = request
        self.cancelled = cancelled
        self.signals = _CompareSignals()

    def run(self) -> None:
        try:
            self._check_cancelled()
            first = checked_image(self.request[0])
            self._check_cancelled()
            second = checked_image(self.request[1])
            self._check_cancelled()
            first, second = align_images(first, second, self.request[2])
            self._check_cancelled()
            result, error = (first, second, difference_image(first, second)), ''
        except (OSError, ValueError, MemoryError) as exception:
            result, error = None, str(exception)
        self.signals.finished.emit(self.request, result, error)

    def _check_cancelled(self) -> None:
        if self.cancelled.is_set():
            raise ValueError('Comparison cancelled')


class CompareView(QGraphicsView):
    """All comparison images share a single transform and pan position."""

    def __init__(self, scene, parent=None) -> None:
        super().__init__(scene, parent)
        self.setBackgroundBrush(QColor('white'))
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def wheelEvent(self, event) -> None:
        factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
        scale = self.transform().m11() * factor
        if 0.02 <= scale <= 32:
            self.scale(factor, factor)
        event.accept()


class _ClippedImage(QGraphicsPixmapItem):
    def __init__(self, pixmap) -> None:
        super().__init__(pixmap)
        self.clip = None

    def paint(self, painter, option, widget=None) -> None:
        painter.save()
        if self.clip is not None:
            painter.setClipRect(self.clip, Qt.ClipOperation.IntersectClip)
        super().paint(painter, option, widget)
        painter.restore()


class ImageCompareDialog(QDialog):
    """Bounded worker decoding; obsolete results never overwrite a newer selection."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.resize(1000, 700)
        self._closed, self._busy = False, False
        self._cancelled = Event()
        self._paths, self._request, self._items = (), None, []
        self._generation, self._loaded_request = 0, None
        retranslator.bind(self, 'image_compare_title', setter='setWindowTitle')
        layout = QVBoxLayout(self)
        self._build_controls(layout)
        self.scene = QGraphicsScene(self)
        self.view = CompareView(self.scene)
        layout.addWidget(self.view)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        hint = tr(QLabel(), 'image_compare_hint')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        retranslator.bind_call(self._retranslate_choices)
        self._retranslate_choices()

    def _build_controls(self, layout) -> None:
        row = QHBoxLayout()
        choose = tr(QPushButton(), 'image_compare_choose')
        choose.clicked.connect(self.choose_images)
        self.mode, self.alignment = QComboBox(), QComboBox()
        for value in ('side', 'overlay', 'wipe', 'difference'):
            self.mode.addItem(value, value)
        for value in ('origin', 'center', 'fit'):
            self.alignment.addItem(value, value)
        self.amount = QSlider(Qt.Orientation.Horizontal)
        self.amount.setRange(0, 100)
        self.amount.setValue(50)
        self.amount.setMaximumWidth(180)
        self.amount_label = QLabel('50%')
        fit = tr(QPushButton(), 'image_compare_fit_view')
        fit.clicked.connect(self.fit_view)
        row.addWidget(choose)
        row.addStretch()
        row.addWidget(fit)
        layout.addLayout(row)
        row = QHBoxLayout()
        for widget in (self.mode, self.alignment, self.amount, self.amount_label):
            row.addWidget(widget)
        layout.addLayout(row)
        self.mode.currentIndexChanged.connect(self.render_mode)
        self.alignment.currentIndexChanged.connect(self._prepare)
        self.amount.valueChanged.connect(self.render_mode)

    def _retranslate_choices(self) -> None:
        for combo, prefix in ((self.mode, 'image_compare_'), (self.alignment, 'image_compare_align_')):
            for index in range(combo.count()):
                combo.setItemText(index, translate(prefix + combo.itemData(index)))

    def choose_images(self) -> None:
        paths, _filter = QFileDialog.getOpenFileNames(self, translate('image_compare_choose'), '',
                                                    'Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif)')
        if paths:
            self.load_paths(paths)

    def load_paths(self, paths: list[str]) -> None:
        """Keep the previous comparison until both newly selected images validate."""
        if len(paths) != 2:
            self.status.setText(translate('image_compare_two'))
            return
        self._paths = tuple(paths)
        self._prepare()

    def _prepare(self, *_args) -> None:
        if self._closed or not self._paths:
            return
        self._generation += 1
        self._request = (*self._paths, self.alignment.currentData(), self._generation)
        if not self._busy:
            self._start_job()

    def _start_job(self) -> None:
        self._busy = True
        self.status.setText(translate('image_compare_loading'))
        job = _CompareJob(self._request, self._cancelled)
        job.signals.finished.connect(self._completed, Qt.ConnectionType.QueuedConnection)
        comparison_pool().start(job)

    def _completed(self, request, images, error: str) -> None:
        self._busy = False
        if self._closed:
            return
        if request != self._request:
            self._start_job()
            return
        if error:
            if self._loaded_request is not None:
                self._paths = self._loaded_request[:2]
                self.alignment.blockSignals(True)
                self.alignment.setCurrentIndex(self.alignment.findData(self._loaded_request[2]))
                self.alignment.blockSignals(False)
            self.status.setText(error)
            return
        self._loaded_request = request
        self.scene.clear()
        self._items = [_ClippedImage(QPixmap.fromImage(image)) for image in images]
        for index, item in enumerate(self._items):
            item.setZValue(index)
            self.scene.addItem(item)
        self.status.setText('A: ' + Path(request[0]).name + ' · B: ' + Path(request[1]).name)
        self.render_mode()
        self.fit_view()

    def render_mode(self, *_args) -> None:
        """Opacity/wipe changes only redraw retained pixmaps; they do not decode again."""
        mode = self.mode.currentData()
        self.amount.setEnabled(mode in ('overlay', 'wipe'))
        self.amount_label.setText(str(self.amount.value()) + '%')
        if not self._items:
            return
        a, b, difference = self._items
        width, height = a.pixmap().width(), a.pixmap().height()
        for item in self._items:
            item.clip = None
            item.setOpacity(1)
            item.setPos(0, 0)
            item.setVisible(mode != 'difference' if item is not difference else mode == 'difference')
        if mode == 'side':
            b.setPos(width + 24, 0)
        elif mode == 'overlay':
            b.setOpacity(self.amount.value() / 100)
        elif mode == 'wipe':
            boundary = width * self.amount.value() / 100
            a.clip = QRectF(0, 0, boundary, height)
            b.clip = QRectF(boundary, 0, width - boundary, height)
        self.scene.setSceneRect(0, 0, width * 2 + 24 if mode == 'side' else width, height)
        self.scene.update()

    def fit_view(self) -> None:
        """Reset pan/zoom and fit the currently displayed comparison extent."""
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def reject(self) -> None:
        self.close()

    def closeEvent(self, event) -> None:
        self._closed = True
        self._cancelled.set()
        self._request, self._paths = None, ()
        self._items.clear()
        self.scene.clear()
        super().closeEvent(event)
