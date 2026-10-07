"""Crop and mark captured pixels, with explicit original/flattened output."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QImage, QPixmap, QPen, QColor, QGuiApplication
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QGraphicsView, QGraphicsScene, QFileDialog, QInputDialog

from frontengine.utils.capture_editor.document import CaptureDocument
from frontengine.utils.multi_language.retranslate import tr, translate, retranslator


class CaptureCanvas(QGraphicsView):
    """Map gestures through the view transform into uncropped image coordinates."""

    changed = Signal()
    failed = Signal(str)

    def __init__(self, document: CaptureDocument, parent=None) -> None:
        super().__init__(parent)
        self.document = document
        self.mode, self.original_view = 'arrow', False
        self.origin, self.rubber = None, None
        self.setScene(QGraphicsScene(self))
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.refresh()

    def refresh(self) -> None:
        """Show exactly the flattened export, or the explicitly selected original."""
        self.origin, self.rubber = None, None
        self.scene().clear()
        image = self.document.original if self.original_view else self.document.render()
        self.scene().addPixmap(QPixmap.fromImage(image))
        self.setSceneRect(QRectF(image.rect()))
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _point(self, event) -> tuple[float, float]:
        point = self.mapToScene(event.position().toPoint())
        return point.x() + self.document.crop.x(), point.y() + self.document.crop.y()

    def mousePressEvent(self, event) -> None:
        if self.original_view or event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        self.origin = self._point(event)
        local = QPointF(self.origin[0]-self.document.crop.x(), self.origin[1]-self.document.crop.y())
        self.rubber = self.scene().addRect(QRectF(local, local), QPen(QColor('#ff3030'), 1))
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self.rubber is None:
            return super().mouseMoveEvent(event)
        point = self._point(event)
        offset = self.document.crop.topLeft()
        self.rubber.setRect(QRectF(QPointF(self.origin[0]-offset.x(), self.origin[1]-offset.y()), QPointF(point[0]-offset.x(), point[1]-offset.y())).normalized())

    def mouseReleaseEvent(self, event) -> None:
        if self.origin is None or event.button() != Qt.MouseButton.LeftButton:
            return super().mouseReleaseEvent(event)
        start, end = self.origin, self._point(event)
        try:
            if self.mode == 'crop':
                self.document.set_crop(start, end)
            else:
                text, accepted = ('', True)
                if self.mode == 'text':
                    text, accepted = QInputDialog.getMultiLineText(self, translate('capture_edit_text'), translate('capture_edit_text'))
                if accepted:
                    self.document.add(self.mode, start, end, text)
        except ValueError as error:
            self.failed.emit(str(error))
        self.refresh()
        self.changed.emit()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)


class CaptureEditor(QDialog):
    """Own a detached capture; only explicit actions export or pin edited pixels."""

    pin_requested = Signal(QImage)

    def __init__(self, image: QImage, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        tr(self, 'capture_edit_title', setter='setWindowTitle')
        self.resize(920, 660)
        self.document = CaptureDocument(image)
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.tools = QComboBox()
        for kind in ('crop', 'arrow', 'number', 'text', 'redact'):
            self.tools.addItem(translate('capture_edit_' + kind), kind)
        self.tools.setCurrentIndex(1)
        row.addWidget(self.tools)
        self.canvas = CaptureCanvas(self.document, self)
        self.tools.currentIndexChanged.connect(self._mode)
        self.original_button = tr(QPushButton(), 'capture_edit_original')
        self.original_button.setCheckable(True)
        self.original_button.toggled.connect(self._show_original)
        row.addWidget(self.original_button)
        for key, callback in [('undo', self._undo), ('reset', self._reset), ('copy', self.copy_result), ('save', self.save_result), ('pin', self.pin_result)]:
            button = tr(QPushButton(), 'capture_edit_' + key)
            button.clicked.connect(callback)
            row.addWidget(button)
        layout.addLayout(row)
        layout.addWidget(self.canvas, 1)
        self.status = tr(QLabel(), 'capture_edit_hint')
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status)
        self.canvas.failed.connect(self._error)
        retranslator.bind_call(self._retranslate)

    def _mode(self) -> None:
        self.canvas.mode = self.tools.currentData()

    def _retranslate(self) -> None:
        for index in range(self.tools.count()):
            self.tools.setItemText(index, translate('capture_edit_' + self.tools.itemData(index)))

    def _show_original(self, value: bool) -> None:
        self.canvas.original_view = value
        self.tools.setEnabled(not value)
        self.canvas.refresh()

    def _undo(self) -> None:
        self.document.undo()
        self.canvas.refresh()

    def _reset(self) -> None:
        self.document.reset()
        self.canvas.refresh()

    def copy_result(self, _checked=False, *, clipboard=None) -> None:
        """Copy flattened edits; a test can inject a clipboard without OS effects."""
        target = clipboard if clipboard is not None else QGuiApplication.clipboard()
        if target is not None:
            target.setImage(self.document.render())
            retranslator.set_text(self.status, 'capture_edit_copied')

    def save_result(self) -> None:
        """Save edited pixels as PNG, with no original or hidden edit layers in the file."""
        path, _filter = QFileDialog.getSaveFileName(self, translate('capture_edit_save'), 'capture-edited.png', 'PNG (*.png)')
        if path:
            if not self.document.save(path):
                self._error(translate('capture_edit_failed'))
            else:
                retranslator.set_text(self.status, 'capture_edit_saved')

    def pin_result(self) -> None:
        """Ask the owning Tools page to pin the same flattened result."""
        self.pin_requested.emit(self.document.render())

    def _error(self, message: str) -> None:
        retranslator.forget(self.status)
        self.status.setText(message)
