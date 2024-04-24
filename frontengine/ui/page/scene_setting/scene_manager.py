import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QPlainTextEdit, QPushButton

from frontengine.user_setting.scene_setting import choose_scene_json, write_scene_file, scene_json
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class SceneManagerUI(QWidget):

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.grid_layout = QGridLayout()
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        # Read and write scene json button
        self.read_scene_json_button = QPushButton(language_wrapper.language_word_dict.get("scene_input"))
        self.read_scene_json_button.clicked.connect(self.update_scene_json)
        self.write_scene_json_button = QPushButton(language_wrapper.language_word_dict.get("scene_output"))
        self.write_scene_json_button.clicked.connect(lambda: write_scene_file(self))
        # Json plaintext
        self.json_plaintext = QPlainTextEdit()
        self.json_plaintext.setReadOnly(True)
        self.json_plaintext.appendPlainText("{}")
        # Add to layout
        self.grid_layout.addWidget(self.json_plaintext, 0, 0, -1, -1)
        self.grid_layout.addWidget(self.read_scene_json_button, 1, 0)
        self.grid_layout.addWidget(self.write_scene_json_button, 1, 1)
        self.setLayout(self.grid_layout)

    def update_scene_json(self):
        choose_scene_json(self)
        self.renew_json_plain_text()

    def renew_json_plain_text(self):
        self.json_plaintext.setPlainText(json.dumps(scene_json, indent=4))
