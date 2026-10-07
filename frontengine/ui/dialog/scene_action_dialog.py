"""Choose scene files, monitor targets and named layer action values."""
from __future__ import annotations

import json

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog,
    QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
)

from frontengine.utils.scene_format.scene_action_values import scene_request, layer_changes
from frontengine.utils.multi_language.retranslate import tr, translate


class SceneActionDialog(QDialog):
    """Build validated values without requiring users to write action JSON."""

    def __init__(self, action: str, value: str, entries: dict, parent=None) -> None:
        super().__init__(parent)
        self.action, self.entries = action, entries
        self.setWindowTitle(translate('rules_choose_target'))
        self.form = QFormLayout(self)
        self.error = QLabel()
        self.error.setWordWrap(True)
        if action in ('scene_load', 'scene_start'):
            self._scene_fields(value)
        else:
            self._layer_fields(value)
        self.form.addRow(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.form.addRow(buttons)

    def _scene_fields(self, value: str) -> None:
        self.path = QLineEdit()
        self.path.setPlaceholderText(translate('rules_scene_current'))
        browse = tr(QPushButton(), 'rules_scene_browse')
        browse.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addWidget(self.path)
        row.addWidget(browse)
        self.form.addRow(translate('rules_scene_path'), row)
        self.screen = QComboBox()
        self.screen.addItem(translate('rules_screen_primary'), 'primary')
        self.screen.addItem(translate('rules_screen_all'), 'all')
        for index, screen in enumerate(QGuiApplication.screens()):
            self.screen.addItem(f'{index}: {screen.name()}', index)
        if self.action == 'scene_start':
            self.form.addRow(translate('rules_scene_screen'), self.screen)
        try:
            path, selected = scene_request(value)
            self.path.setText(path)
            self.screen.setCurrentIndex(max(0, self.screen.findData(selected)))
        except ValueError as error:
            self.error.setText(str(error))

    def _browse(self) -> None:
        path, _filter = QFileDialog.getOpenFileName(self, translate('rules_scene_path'),
                                                 filter='Scene (*.json *.fescene *.puppet)')
        if path:
            self.path.setText(path)

    def _layer_fields(self, value: str) -> None:
        self.layer = QComboBox()
        self.layer.setEditable(True)
        self.layer.addItems(list(self.entries))
        self.form.addRow(translate('rules_layer_key'), self.layer)
        self.fields = {}
        names = ('opacity',) if self.action == 'layer_opacity' else ('x', 'y')
        if self.action in ('layer_show', 'layer_hide'):
            names = ()
        for name in names:
            field = QDoubleSpinBox()
            field.setRange(0, 100) if name == 'opacity' else field.setRange(-100000, 100000)
            field.setDecimals(2)
            self.fields[name] = field
            self.form.addRow(translate('scene_property_' + name), field)
        self.layer.currentTextChanged.connect(self._layer_defaults)
        self._layer_defaults(self.layer.currentText())
        if not value:
            return
        try:
            key, changes = layer_changes(self.action, value)
            self.layer.setCurrentText(key)
            for name, field in self.fields.items():
                field.setValue(changes.get(name, field.value()))
        except ValueError as error:
            self.error.setText(str(error))

    def _layer_defaults(self, key: str) -> None:
        entry = self.entries.get(key, {})
        for name, field in self.fields.items():
            field.setValue(entry.get(name, 100 if name == 'opacity' else 0))

    def action_value(self) -> str:
        """Return the portable value stored in the rule, never a widget reference."""
        if self.action in ('scene_load', 'scene_start'):
            data = {'path': self.path.text().strip()}
            if self.action == 'scene_start':
                data['screen'] = self.screen.currentData()
            return json.dumps(data, ensure_ascii=False)
        key = self.layer.currentText()
        if self.action in ('layer_show', 'layer_hide'):
            return key
        return json.dumps({'layer': key, **{name: field.value() for name, field in self.fields.items()}},
                          ensure_ascii=False)

    def accept(self) -> None:
        try:
            value = self.action_value()
            if self.action in ('scene_load', 'scene_start'):
                scene_request(value, load_only=self.action == 'scene_load')
            else:
                layer_changes(self.action, value)
        except ValueError as error:
            self.error.setText(str(error))
            return
        super().accept()
