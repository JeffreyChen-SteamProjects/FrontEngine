"""Edit a layer's bounded animation tracks as one undoable scene change."""
from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDoubleSpinBox, QTableWidget, QTableWidgetItem, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox, QLabel

from frontengine.utils.multi_language.retranslate import tr, translate, retranslator
from frontengine.utils.scene_format.scene_animation import CHANNELS, MAX_KEYFRAMES, base_values, validate_animation


class SceneAnimationDialog(QDialog):
    """Blank cells leave channels unchanged; times must be strictly increasing."""

    def __init__(self, document, key: str, parent=None) -> None:
        super().__init__(parent)
        self.document, self.key = document, key
        tr(self, 'scene_animation_edit', setter='setWindowTitle')
        self.resize(720, 450)
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 5)
        self._headers()
        retranslator.bind_call(self._headers)
        layout.addWidget(self.table)
        row = QHBoxLayout()
        self.seconds = QDoubleSpinBox()
        self.seconds.setRange(.1, 60)
        self.seconds.setValue(1)
        row.addWidget(tr(QLabel(), 'scene_animation_duration'))
        row.addWidget(self.seconds)
        for label, action in [('scene_animation_add', self._add), ('scene_animation_remove', self._remove),
                              ('scene_animation_fade', lambda: self._preset(True)),
                              ('scene_animation_slide', lambda: self._preset(False)),
                              ('scene_animation_apply', self._apply)]:
            button = tr(QPushButton(), label)
            button.clicked.connect(action)
            row.addWidget(button)
        layout.addLayout(row)
        self._fill(document.entries[key].get('animation', []))

    def _headers(self) -> None:
        self.table.setHorizontalHeaderLabels([translate('scene_animation_time'),
            *(translate('scene_property_' + field) for field in CHANNELS), translate('scene_animation_easing')])

    def _fill(self, frames: list[dict]) -> None:
        self.table.setRowCount(len(frames))
        for index, frame in enumerate(frames):
            for column, field in enumerate(('time', *CHANNELS, 'easing')):
                default = 'linear' if field == 'easing' else ''
                self.table.setItem(index, column, QTableWidgetItem(str(frame.get(field, default))))

    def _add(self) -> None:
        if self.table.rowCount() >= MAX_KEYFRAMES:
            QMessageBox.warning(self, self.windowTitle(), translate('scene_animation_limit'))
            return
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(str(row)))
        self.table.setItem(row, 4, QTableWidgetItem('linear'))

    def _remove(self) -> None:
        for row in sorted({item.row() for item in self.table.selectedItems()}, reverse=True):
            self.table.removeRow(row)

    def _preset(self, fade: bool) -> None:
        entry = self.document.entries.get(self.key)
        if entry is None:
            return
        values = base_values(entry)
        start = {**values, 'opacity': 0} if fade else {**values, 'x': max(-100000, values['x'] - 160)}
        self._fill([{'time': 0, **start}, {'time': self.seconds.value(), **values, 'easing': 'smooth'}])

    def _frames(self) -> list[dict]:
        frames = []
        for row in range(self.table.rowCount()):
            frame = {}
            for column, field in enumerate(('time', *CHANNELS, 'easing')):
                item = self.table.item(row, column)
                text = item.text().strip() if item is not None else ''
                if text:
                    frame[field] = text if field == 'easing' else float(text)
            frames.append(frame)
        return validate_animation(frames)

    def _apply(self) -> None:
        try:
            if self.document.entries.get(self.key, {}).get('locked'):
                raise ValueError('The layer is locked')
            self.document.update(self.key, {'animation': self._frames()}, 'Edit animation')
        except (ValueError, OverflowError) as error:
            QMessageBox.warning(self, self.windowTitle(), str(error))
            return
        self.accept()
