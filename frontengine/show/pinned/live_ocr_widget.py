"""Live OCR text next to an explicitly selected region, with bounded local history."""
from __future__ import annotations

from datetime import datetime
from PySide6.QtCore import QRect, QTimer, Qt, Signal
from PySide6.QtGui import QGuiApplication, QImage
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox, QSpinBox, QPlainTextEdit, QComboBox

from frontengine.utils.screen_text.live_ocr import RegionSource, LiveOcrSession
from frontengine.utils.multi_language.retranslate import tr, translate, retranslator


class LiveOcrWidget(QDialog):
    """Manual by default, one request at a time, twenty unique successful text results."""

    consent_requested = Signal(str)

    def __init__(self, region: QRect, reader, *, source=None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        tr(self, 'live_ocr_title', setter='setWindowTitle')
        self.resize(520, 420)
        self.region, self.closed, self.busy = QRect(region), False, False
        self.current_text, self.history, self.consent_kind = '', [], ''
        self.source = source or RegionSource(self)
        self.source.frame.connect(self._captured)
        self.source.failed.connect(self._failed)
        self.session = LiveOcrSession(reader, self)
        self.session.completed.connect(self._completed)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        layout = QVBoxLayout(self)
        self._build_controls(layout)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        layout.addWidget(self.text, 1)
        self.history_box = QComboBox()
        self.history_box.currentIndexChanged.connect(self._show_history)
        layout.addWidget(self.history_box)
        self.status = tr(QLabel(), 'live_ocr_hint')
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status)

    def _build_controls(self, layout) -> None:
        row = QHBoxLayout()
        self.refresh_button = tr(QPushButton(), 'live_ocr_refresh')
        self.refresh_button.clicked.connect(self.refresh)
        self.copy_button = tr(QPushButton(), 'live_ocr_copy')
        self.copy_button.clicked.connect(self.copy_text)
        self.automatic = tr(QCheckBox(), 'live_ocr_auto')
        self.interval = QSpinBox()
        self.interval.setRange(5, 60)
        self.interval.setSuffix(' s')
        self.interval.setValue(10)
        self.automatic.toggled.connect(self._schedule)
        self.interval.valueChanged.connect(self._schedule)
        for widget in (self.refresh_button, self.copy_button, self.automatic, self.interval):
            row.addWidget(widget)
        layout.addLayout(row)
        self.cloud = tr(QCheckBox(), 'live_ocr_cloud')
        self.cloud.toggled.connect(self._cloud_changed)
        layout.addWidget(self.cloud)
        self.consent_button = tr(QPushButton(), 'live_ocr_consent')
        self.consent_button.setEnabled(False)
        self.consent_button.clicked.connect(lambda: self.consent_requested.emit(self.consent_kind))
        layout.addWidget(self.consent_button)

    def _cloud_changed(self) -> None:
        self.consent_kind = ''
        self.consent_button.setEnabled(False)
        retranslator.set_text(self.status, 'live_ocr_hint')

    def _schedule(self, *_args) -> None:
        self.timer.stop()
        if not self.closed and self.isVisible() and self.automatic.isChecked():
            self.timer.start(self.interval.value()*1000)

    def refresh(self) -> None:
        """Capture only visible explicit regions; slow OCR skips repeated requests."""
        if self.closed or self.busy or not self.isVisible():
            return
        if self.frameGeometry().intersects(self.region):
            self._failed(translate('live_ocr_overlap'))
            return
        self.busy = True
        self.refresh_button.setEnabled(False)
        retranslator.set_text(self.status, 'live_ocr_working')
        try:
            self.source.start(self.region)
        except Exception as error:
            self._failed(str(error))

    def _captured(self, image: QImage) -> None:
        if not self.closed and self.busy and self.isVisible():
            self.source.stop()
            self.session.submit(image, cloud=self.cloud.isChecked())
        else:
            self.source.stop()

    def _completed(self, result) -> None:
        if self.closed:
            return
        self.busy = False
        self.refresh_button.setEnabled(True)
        self.consent_kind = result.consent_required if self.cloud.isChecked() else ''
        self.consent_button.setEnabled(bool(self.consent_kind))
        if result.status != 'success':
            self._failed(result.error or result.status)
            return
        changed = result.text != self.current_text
        self.current_text = result.text
        self.text.setPlainText(result.text)
        if result.text and changed:
            self.history = [entry for entry in self.history if entry['text'] != result.text]
            self.history.insert(0, {'at': datetime.now().strftime('%H:%M:%S'), 'text': result.text})
            del self.history[20:]
            self._history_rows()
        key = 'live_ocr_updated' if changed else 'live_ocr_unchanged'
        retranslator.forget(self.status)
        self.status.setText(translate(key).format(backend=result.backend))

    def _history_rows(self) -> None:
        self.history_box.blockSignals(True)
        self.history_box.clear()
        for entry in self.history:
            self.history_box.addItem(entry['at']+' '+entry['text'].replace('\n', ' ')[:60], entry['text'])
        self.history_box.blockSignals(False)

    def _show_history(self, index: int) -> None:
        text = self.history_box.itemData(index)
        if text is not None:
            self.text.setPlainText(text)

    def _failed(self, reason: str) -> None:
        if self.closed:
            return
        self.busy = False
        self.refresh_button.setEnabled(True)
        self.source.stop()
        retranslator.forget(self.status)
        self.status.setText(reason)

    def copy_text(self, _checked=False, *, clipboard=None) -> None:
        """Copy the displayed current or historical text only on an explicit action."""
        target = clipboard if clipboard is not None else QGuiApplication.clipboard()
        if target is not None:
            target.setText(self.text.toPlainText())

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._schedule()

    def hideEvent(self, event) -> None:
        self.timer.stop()
        self.source.stop()
        if not self.session.busy:
            self.busy = False
            self.refresh_button.setEnabled(True)
        super().hideEvent(event)

    def _shutdown(self) -> None:
        self.closed = True
        self.timer.stop()
        self.source.stop()
        self.session.close()
        self.history.clear()

    def done(self, result: int) -> None:
        self._shutdown()
        super().done(result)

    def closeEvent(self, event) -> None:
        self._shutdown()
        super().closeEvent(event)
