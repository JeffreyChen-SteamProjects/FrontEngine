"""Explicit fixed-resolution preview and asynchronous virtual-camera output."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, QRunnable, QThreadPool, QObject, Signal
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox, QPushButton, QColorDialog

from frontengine.show.scene.render_session import SceneRenderSession, OUTPUT_SIZES
from frontengine.utils.virtual_camera.frame_sender import FrameSender
from frontengine.utils.recording.frame_recorder import image_to_rgb
from frontengine.utils.multi_language.retranslate import tr, retranslator, translate
from frontengine.utils.scene_format.scene_resource_reads import SceneResourceRead


class _PreparationSignals(QObject):
    finished = Signal(int, object, object, str)


class _OutputPreparation(QRunnable):
    def __init__(self, generation, document, signals):
        super().__init__()
        self.generation, self.document, self.signals = generation, document, signals
        self.read = SceneResourceRead(document)

    def run(self):
        try:
            from frontengine.show.scene.runtime3d import prepare_models
            models = prepare_models(self.document)
            self.signals.finished.emit(self.generation, self.document, models, '')
        except Exception as error:
            self.signals.finished.emit(self.generation, self.document, None, str(error))
        finally:
            self.read.close()


class SceneOutputDialog(QDialog):
    """Close the snapshot before scene edits/extraction leases change underneath it."""

    def __init__(self, document, parent=None, *, renderer=SceneRenderSession, sender_factory=FrameSender) -> None:
        super().__init__(parent)
        self.document, self.renderer, self.sender_factory = document, renderer, sender_factory
        self.session, self.sender = None, None
        self.generation, self.preparing, self.send_after_prepare = 0, False, False
        self.background = QColor('black')
        self.preparation_signals = _PreparationSignals()
        self.preparation_signals.finished.connect(self._prepared, Qt.ConnectionType.QueuedConnection)
        self.stopping_senders = set()
        tr(self, 'scene_camera_output', setter='setWindowTitle')
        self.resize(720, 560)
        layout = QVBoxLayout(self)
        self.preview = QLabel()
        self.preview.setMinimumSize(320, 180)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.preview, 1)
        self.resolution = QComboBox()
        for size in OUTPUT_SIZES:
            self.resolution.addItem(f'{size[0]}×{size[1]}', size)
        self.fps = QSpinBox()
        self.fps.setRange(5, 60)
        self.fps.setValue(20)
        row = QHBoxLayout()
        row.addWidget(self.resolution)
        row.addWidget(tr(QLabel(), 'tools_fps'))
        row.addWidget(self.fps)
        background_button = tr(QPushButton(), 'scene3d_output_background', 'Camera background')
        background_button.clicked.connect(self._background)
        row.addWidget(background_button)
        self.buttons = {}
        for key, callback in [('scene_output_preview', self.start_preview),
                              ('scene_output_send', self.send_camera), ('scene_output_stop', self.stop)]:
            button = tr(QPushButton(), key)
            button.clicked.connect(callback)
            row.addWidget(button)
            self.buttons[key] = button
        layout.addLayout(row)
        self.status = tr(QLabel(), 'scene_output_hint')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh)
        document.changed.connect(self._scene_changed)

    def start_preview(self) -> None:
        """Start only on user intent; previews never open a camera or play audio."""
        self.stop()
        if self.document.scene.mode == '3d':
            self.preparing = True
            self.resolution.setEnabled(False)
            self.fps.setEnabled(False)
            retranslator.set_text(self.status, 'scene_action_loading')
            QThreadPool.globalInstance().start(_OutputPreparation(
                self.generation, self.document.scene.copy(), self.preparation_signals))
            return
        self._start_session(self.document.entries)

    def _prepared(self, generation, document, models, error):
        if generation != self.generation or not self.preparing:
            return
        self.preparing = False
        if error:
            self.resolution.setEnabled(True)
            self.fps.setEnabled(True)
            self._error(error)
            return
        self._start_session(document, models)
        if self.send_after_prepare and self.session is not None:
            self.send_after_prepare = False
            self.send_camera()

    def _start_session(self, data, models=None):
        try:
            kwargs = {'models': models} if models is not None else {}
            self.session = self.renderer(data, tuple(self.resolution.currentData()), self, **kwargs)
        except Exception as error:
            self.resolution.setEnabled(True)
            self.fps.setEnabled(True)
            self._error(str(error))
            return
        self.session.failed.connect(self._error)
        self.resolution.setEnabled(False)
        self.fps.setEnabled(False)
        self.timer.start(1000 // self.fps.value())
        retranslator.set_text(self.status, 'scene_output_previewing')
        self._refresh()

    def send_camera(self) -> None:
        """Open the fixed-size camera asynchronously and retain one latest frame."""
        if self.sender is not None or self.stopping_senders:
            return
        if self.session is None:
            if not self.preparing:
                self.start_preview()
            if self.preparing:
                self.send_after_prepare = True
        if self.session is None:
            return
        width, height = self.resolution.currentData()
        sender = self.sender_factory(width, height, self.fps.value(), self)
        self.sender = sender
        sender.ready.connect(lambda device: self._ready(sender, device), Qt.ConnectionType.QueuedConnection)
        sender.failed.connect(lambda error: self._sender_failed(sender, error), Qt.ConnectionType.QueuedConnection)
        sender.finished.connect(lambda: self._finished(sender), Qt.ConnectionType.QueuedConnection)
        retranslator.set_text(self.status, 'scene_output_starting')
        self.buttons['scene_output_send'].setEnabled(False)
        sender.start()
        self._refresh()

    def _ready(self, sender, device: str) -> None:
        if sender is self.sender:
            retranslator.forget(self.status)
            self.status.setText(translate('tools_vcam_sending').format(device=device))

    def _sender_failed(self, sender, error: str) -> None:
        if sender is self.sender:
            self._error(error)

    def _finished(self, sender) -> None:
        self.stopping_senders.discard(sender)
        if sender is self.sender:
            self.sender = None
        sender.deleteLater()
        self.buttons['scene_output_send'].setEnabled(not self.stopping_senders and self.sender is None)

    def _error(self, error: str) -> None:
        retranslator.forget(self.status)
        self.status.setText(error)

    def _refresh(self) -> None:
        if self.session is None:
            return
        try:
            frame = self.session.frame()
        except Exception as error:
            self.stop()
            self._error(str(error))
            return
        if frame.isNull():
            return
        self.preview.setPixmap(QPixmap.fromImage(frame).scaled(self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio))
        if self.sender is not None:
            if frame.hasAlphaChannel():
                from PySide6.QtGui import QImage, QPainter
                opaque = QImage(frame.size(), QImage.Format.Format_RGB32)
                opaque.fill(self.background)
                painter = QPainter(opaque)
                painter.drawImage(0, 0, frame)
                painter.end()
                frame = opaque
            self.sender.submit(image_to_rgb(frame))

    def _background(self):
        color = QColorDialog.getColor(self.background, self, translate('scene3d_output_background', 'Camera background'))
        if color.isValid():
            self.background = color

    def _scene_changed(self, _entries: dict) -> None:
        if self.session is not None or self.sender is not None or self.preparing:
            self.stop()
            retranslator.set_text(self.status, 'scene_output_changed')

    def stop(self) -> None:
        """Stop timers/device requests before closing renderer and shared asset readers."""
        self.timer.stop()
        self.generation += 1
        self.preparing, self.send_after_prepare = False, False
        if self.sender is not None:
            sender, self.sender = self.sender, None
            self.stopping_senders.add(sender)
            sender.stop()
        if self.session is not None:
            self.session.close()
            self.session.deleteLater()
            self.session = None
        self.preview.clear()
        self.resolution.setEnabled(True)
        self.fps.setEnabled(True)
        self.buttons['scene_output_send'].setEnabled(not self.stopping_senders)
        retranslator.set_text(self.status, 'scene_output_hint')

    def closeEvent(self, event) -> None:
        self.stop()
        super().closeEvent(event)

    def done(self, result: int) -> None:
        """Escape/reject also releases output, even without a close event."""
        self.stop()
        super().done(result)
