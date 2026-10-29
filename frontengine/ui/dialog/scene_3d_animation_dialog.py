"""Numeric, undoable 3D keyframes without exposing the JSON wire format."""
from copy import deepcopy

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QTableWidget,
                              QTableWidgetItem, QPushButton, QMessageBox, QDialogButtonBox)
from frontengine.utils.multi_language.retranslate import tr, translate, retranslator
from frontengine.show.scene.math3d import euler_quaternion, quaternion_euler


class Scene3DAnimationDialog(QDialog):
    def __init__(self, document, key, parent=None):
        super().__init__(parent)
        self.document, self.key = document, key
        self.tracks = deepcopy(document.entries[key].get('tracks', {}))
        self.channel = 'position'
        tr(self, 'scene_animation_title', setter='setWindowTitle')
        self.resize(650, 420)
        layout = QVBoxLayout(self)
        self.channels = QComboBox()
        channels = ['position', 'rotation', 'scale3d', 'opacity']
        kind = document.entries[key]['type']
        if kind == 'CAMERA':
            channels += ['fov']
        if kind == 'LIGHT':
            channels += ['color', 'intensity']
        for channel in channels:
            self.channels.addItem(translate('scene3d_track_'+channel, channel), channel)
            retranslator.bind(self.channels, 'scene3d_track_'+channel, channel, 'setItemText', self.channels.count()-1)
        self.channels.currentIndexChanged.connect(self._switch)
        layout.addWidget(self.channels)
        self.table = QTableWidget(0, 5)
        retranslator.bind_call(self._headers)
        layout.addWidget(self.table)
        row = QHBoxLayout()
        for label, callback in (('scene3d_key_add', self._add), ('scene3d_key_remove', self._remove)):
            button = tr(QPushButton(), label)
            button.clicked.connect(callback)
            row.addWidget(button)
        layout.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._load()

    def _load(self):
        vector = self.channel in ('position', 'rotation', 'scale3d', 'color')
        self.table.setColumnCount(5 if vector else 3)
        self._headers()
        self.table.setRowCount(0)
        for frame in self.tracks.get(self.channel, []):
            self._append(frame)

    def _headers(self):
        labels = ['R', 'G', 'B'] if self.channel == 'color' else ['X', 'Y', 'Z']
        values = labels if self.channel in ('position', 'rotation', 'scale3d', 'color') else [translate('scene3d_value', 'Value')]
        self.table.setHorizontalHeaderLabels([translate('scene_animation_time'), *values, translate('scene_animation_easing')])

    def _append(self, frame):
        row = self.table.rowCount()
        self.table.insertRow(row)
        value = frame['value']
        if self.channel == 'rotation':
            value = quaternion_euler(value)
        values = [frame['time'], *(value if isinstance(value, list) else [value])]
        for column, value in enumerate(values):
            self.table.setItem(row, column, QTableWidgetItem(str(round(value, 6))))
        easing = QComboBox()
        for mode in ('linear', 'smooth', 'step'):
            easing.addItem(translate('scene3d_'+mode, mode), mode)
            retranslator.bind(easing, 'scene3d_'+mode, mode, 'setItemText', easing.count()-1)
        easing.setCurrentIndex(easing.findData(frame.get('easing', 'linear')))
        self.table.setCellWidget(row, self.table.columnCount()-1, easing)

    def _collect(self):
        result = []
        for row in range(self.table.rowCount()):
            values = [float(self.table.item(row, column).text()) for column in range(self.table.columnCount()-1)]
            value = values[1:] if len(values) > 2 else values[1]
            if self.channel == 'rotation':
                value = euler_quaternion(value)
            result.append({'time': values[0], 'value': value,
                           'easing': self.table.cellWidget(row, self.table.columnCount()-1).currentData()})
        result.sort(key=lambda f: f['time'])
        if result:
            self.tracks[self.channel] = result
        else:
            self.tracks.pop(self.channel, None)

    def _switch(self):
        try:
            self._collect()
        except (ValueError, AttributeError) as error:
            QMessageBox.warning(self, translate('scene_animation_title'), str(error))
            self.channels.blockSignals(True)
            self.channels.setCurrentIndex(self.channels.findData(self.channel))
            self.channels.blockSignals(False)
            return
        self.channel = self.channels.currentData()
        self._load()

    def _add(self):
        entry = self.document.entries[self.key]
        value = entry.get('transform', {}).get({'position': 'position', 'rotation': 'rotation', 'scale3d': 'scale'}.get(self.channel),
                entry.get(self.channel, [1, 1, 1] if self.channel == 'color' else 100 if self.channel == 'opacity' else 45 if self.channel == 'fov' else 1))
        self._append({'time': self.table.rowCount(), 'value': value})

    def _remove(self):
        for row in sorted({item.row() for item in self.table.selectedItems()}, reverse=True):
            self.table.removeRow(row)

    def _save(self):
        try:
            if self.document.entries.get(self.key, {}).get('locked'):
                raise ValueError('The scene object is locked')
            self._collect()
            self.document.update(self.key, {'tracks': self.tracks}, 'Edit 3D keyframes')
        except (ValueError, AttributeError) as error:
            QMessageBox.warning(self, translate('scene_animation_title'), str(error))
            return
        self.accept()
