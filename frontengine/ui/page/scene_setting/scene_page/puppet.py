"""Author a scene entry pointing at the shared Imervue puppet format."""
import json

from PySide6.QtWidgets import QFileDialog, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QSpinBox

from frontengine.ui.page.layout_kit import SettingPage
from frontengine.user_setting.scene_setting import scene_json
from frontengine.utils.imervue.puppet_asset import finite_parameters, validate_puppet
from frontengine.utils.multi_language.retranslate import tr


class PuppetSceneSettingUI(SettingPage):
    def __init__(self, script_ui) -> None:
        super().__init__('scene_puppet', 'scene_puppet_hint', 'Puppet', 'Use an Imervue character in this scene.')
        self.script_ui = script_ui
        self.path = QLineEdit()
        self.script_path = QLineEdit()
        self.motion = QLineEdit()
        self.expression = QLineEdit()
        self.parameters = QPlainTextEdit('{}')
        self.x, self.y, self.width, self.height, self.opacity = [QSpinBox() for _ in range(5)]
        self.x.setRange(-32768, 32768)
        self.y.setRange(-32768, 32768)
        self.width.setRange(16, 4096)
        self.height.setRange(16, 4096)
        self.width.setValue(320)
        self.height.setValue(480)
        self.opacity.setRange(0, 100)
        self.opacity.setValue(100)
        choose = tr(QPushButton(), 'scene_puppet_choose', 'Choose .puppet...')
        choose.clicked.connect(self.choose_puppet)
        source = self.add_section('section_source', 'Source')
        source.add_inline(choose, self.path)
        source.add_row('pet_choose_script', self.script_path, 'Pet script path (optional)')
        details = self.add_section('section_appearance', 'Appearance')
        for key, widget, fallback in (
                ('scene_x', self.x, 'X'), ('scene_y', self.y, 'Y'),
                ('scene_width', self.width, 'Width'), ('scene_height', self.height, 'Height'),
                ('scene_opacity', self.opacity, 'Opacity (%)'), ('scene_motion', self.motion, 'Motion'),
                ('scene_expression', self.expression, 'Expression')):
            details.add_row(key, widget, fallback)
        details.add_row('scene_parameters', self.parameters, 'Parameters (JSON)')
        append = tr(QPushButton(), 'scene_puppet_add', 'Add puppet to scene')
        append.clicked.connect(self.append_entry)
        details.add_inline(append)

    def choose_puppet(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Imervue puppet', '', 'Imervue puppet (*.puppet)')
        if path:
            self.path.setText(path)

    def append_entry(self) -> None:
        try:
            validate_puppet(self.path.text())
            values = finite_parameters(json.loads(self.parameters.toPlainText()))
        except (ValueError, OSError) as error:
            QMessageBox.warning(self, 'Puppet Error', str(error))
            return
        entry = {'type': 'PUPPET', 'file_path': self.path.text(),
                 'x': self.x.value(), 'y': self.y.value(),
                 'size': [self.width.value(), self.height.value()],
                 'opacity': self.opacity.value(), 'parameters': values}
        for field, widget in (('motion', self.motion), ('expression', self.expression),
                              ('script_path', self.script_path)):
            if widget.text().strip():
                entry[field] = widget.text().strip()
        index = 0
        while str(index) in scene_json:
            index += 1
        scene_json[str(index)] = entry
        self.script_ui.renew_json_plain_text()
