"""Opt-in image clipboard history, with explicit reuse and bounded thumbnail lists."""
from __future__ import annotations
from datetime import datetime

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QIcon, QPixmap
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QSpinBox, QPushButton, QListWidget, QListWidgetItem, QAbstractItemView, QLineEdit

from frontengine.utils.multi_language.retranslate import tr, retranslator


class ImageHistoryDialog(QDialog):
    """Explicit settings and one reusable owner window; no history recording on open."""

    def __init__(self, service, parent=None, *, clipboard_provider=QGuiApplication.clipboard,
                 capture_mode: bool = False) -> None:
        super().__init__(parent)
        self.service, self.clipboard_provider = service, clipboard_provider
        self.capture_mode = capture_mode
        self.image_busy = False
        tr(self, 'capture_history_title' if capture_mode else 'image_history_title', setter='setWindowTitle')
        self.resize(800, 600)
        layout = QVBoxLayout(self)
        self._build_settings(layout)
        self._build_search(layout)
        self.entries = QListWidget()
        self.entries.setViewMode(QListWidget.ViewMode.IconMode)
        self.entries.setIconSize(QSize(160, 120))
        self.entries.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.entries.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.entries, 1)
        row = QHBoxLayout()
        self.action_buttons = []
        for key, callback in [('image_history_copy', lambda: self._get_image('copy')),
                              ('image_history_pin', lambda: self._get_image('pin')),
                              ('image_history_board', lambda: self._get_image('board')),
                              ('image_history_favorite', self._favorite),
                              ('image_history_remove', self._remove), ('image_history_clear', self._clear)]:
            button = tr(QPushButton(), key)
            button.clicked.connect(callback)
            row.addWidget(button)
            self.action_buttons.append(button)
        layout.addLayout(row)
        self.status = tr(QLabel(), 'capture_history_hint' if capture_mode else 'image_history_hint')
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status)
        self.service.result.connect(self._result)
        self.service.failed.connect(self._failed)

    def _build_settings(self, layout) -> None:
        row = QHBoxLayout()
        self.enabled = tr(QCheckBox(), 'capture_history_enable' if self.capture_mode else 'image_history_enable')
        self.persist = tr(QCheckBox(), 'image_history_persist')
        self.limit, self.capacity = QSpinBox(), QSpinBox()
        self.limit.setRange(10, 200)
        self.capacity.setRange(8, 128)
        self.apply_button = tr(QPushButton(), 'image_history_apply')
        self.apply_button.clicked.connect(self._configure)
        for widget in (self.enabled, self.persist, tr(QLabel(), 'image_history_limit'), self.limit,
                       tr(QLabel(), 'image_history_capacity'), self.capacity, self.apply_button):
            row.addWidget(widget)
        layout.addLayout(row)

    def _build_search(self, layout) -> None:
        self.search, self.date = QLineEdit(), QLineEdit()
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(250)
        self.search_timer.timeout.connect(self.reload)
        if not self.capture_mode:
            return
        row = QHBoxLayout()
        for label, field in (('capture_history_text', self.search), ('capture_history_date', self.date)):
            field.setMaxLength(256)
            row.addWidget(tr(QLabel(), label))
            row.addWidget(field)
            field.textChanged.connect(lambda: self.search_timer.start())
        layout.addLayout(row)

    def _config_fields(self) -> None:
        config = self.service.config
        self.enabled.setChecked(config['enabled'])
        self.persist.setChecked(config['persistent'])
        self.limit.setValue(config['limit'])
        self.capacity.setValue(config['capacity_mib'])

    def _configure(self) -> None:
        self.apply_button.setEnabled(False)
        self.service.request('configure', enabled=self.enabled.isChecked(), persistent=self.persist.isChecked(),
                             limit=self.limit.value(), capacity_mib=self.capacity.value())

    def _selected(self):
        item = self.entries.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def reload(self) -> None:
        """Read thumbnails on the worker; the GUI list never opens full image files."""
        self.service.request('list', text=self.search.text().strip(), date=self.date.text().strip())

    def _get_image(self, action: str) -> None:
        selected = self._selected()
        if selected is not None and not self.image_busy:
            self.image_busy = True
            for button in self.action_buttons:
                button.setEnabled(False)
            self.service.request('image', id=selected['id'], action=action)

    def _favorite(self) -> None:
        entry = self._selected()
        if entry is not None:
            self.service.request('pin', id=entry['id'], value=not entry['pinned'])

    def _remove(self) -> None:
        entry = self._selected()
        if entry is not None:
            self.service.request('remove', id=entry['id'])

    def _clear(self) -> None:
        self.service.request('clear')

    def _result(self, kind: str, value) -> None:
        if kind == 'configure':
            self.apply_button.setEnabled(True)
            self._config_fields()
        if not self.isVisible():
            return
        if kind == 'list':
            self._show_entries(value)
        elif kind == 'image':
            self._use_image(value)
        elif kind in ('capture', 'configure', 'clear', 'remove', 'pin'):
            if kind == 'capture' and self.capture_mode and isinstance(value, dict):
                if value['error']:
                    retranslator.set_text(self.status, 'capture_history_unindexed')
                    self.status.setToolTip(value['error'])
                else:
                    retranslator.set_text(self.status, 'capture_history_indexed')
                    self.status.setToolTip('')
            self.reload()

    def _show_entries(self, values: list) -> None:
        selected = self._selected()
        self.entries.clear()
        for entry in values:
            at = datetime.fromisoformat(entry['at']).astimezone().strftime('%Y-%m-%d %H:%M:%S')
            item = QListWidgetItem(QIcon(QPixmap.fromImage(entry['thumbnail'])), ('★ ' if entry['pinned'] else '') + at)
            item.setData(Qt.ItemDataRole.UserRole, {'id': entry['id'], 'pinned': entry['pinned']})
            item.setToolTip(entry['at'] + '\n' + entry['text'][:500])
            self.entries.addItem(item)
            if selected is not None and selected['id'] == entry['id']:
                self.entries.setCurrentItem(item)

    def _use_image(self, value: dict) -> None:
        self.image_busy = False
        for button in self.action_buttons:
            button.setEnabled(True)
        if value['action'] == 'copy':
            clipboard = self.clipboard_provider()
            if clipboard is not None:
                clipboard.setImage(value['image'])
        elif value['action'] == 'pin':
            self.parent().tools_setting_ui._pin_edited_capture(value['image'])
        elif value['action'] == 'board':
            self.parent().image_setting_ui.add_reference_image(value['image'])

    def _failed(self, kind: str, message: str) -> None:
        self.apply_button.setEnabled(True)
        if kind == 'configure':
            self._config_fields()
        if kind == 'image':
            self.image_busy = False
            for button in self.action_buttons:
                button.setEnabled(True)
        if self.isVisible():
            retranslator.forget(self.status)
            self.status.setText(message)

    def showEvent(self, event) -> None:
        self._config_fields()
        self.image_busy = False
        for button in self.action_buttons:
            button.setEnabled(True)
        self.reload()
        super().showEvent(event)

    def done(self, result: int) -> None:
        self.search_timer.stop()
        self.entries.clear()
        self.image_busy = False
        super().done(result)

    def closeEvent(self, event) -> None:
        self.search_timer.stop()
        self.entries.clear()
        super().closeEvent(event)
