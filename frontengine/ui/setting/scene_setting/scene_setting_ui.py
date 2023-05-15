from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton

from frontengine.show.scene.scene import SceneManager
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class SceneSettingUI(QWidget):

    def __init__(self):
        super().__init__()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        # Init variable
        self.scene_list = list()
        # Start button
        self.start_button = QPushButton(
            language_wrapper.language_word_dict.get("scene_setting_start_scene_button")
        )
        self.start_button.clicked.connect(self.start_scene)
        # Add to layout
        self.grid_layout.addWidget(self.start_button, 0, 0)
        self.setLayout(self.grid_layout)

    def start_scene(self):
        scene = SceneManager()
        self.scene_list.append(scene)
