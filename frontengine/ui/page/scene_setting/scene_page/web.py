from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QSlider, QLabel, QLineEdit, QMessageBox, QPushButton

from frontengine.ui.page.scene_setting.scene_manager import SceneManagerUI
from frontengine.user_setting.scene_setting import scene_json
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class WebSceneSettingUI(QWidget):

    def __init__(self, script_ui: SceneManagerUI):
        super().__init__()
        self.script_ui = script_ui
        # Opacity setting
        self.opacity_slider = QSlider()
        self.opacity_slider.setOrientation(Qt.Orientation.Horizontal)
        self.opacity_label = QLabel(
            language_wrapper.language_word_dict.get("Opacity")
        )
        self.opacity_slider.setMinimum(1)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(20)
        self.opacity_slider.setTickInterval(1)
        self.opacity_slider_value_label = QLabel(str(self.opacity_slider.value()))
        self.opacity_slider.actionTriggered.connect(self.opacity_trick)
        # WEB URL input
        self.web_url_input = QLineEdit()
        self.url_label = QLabel(
            language_wrapper.language_word_dict.get("scene_url_label")
        )
        self.grid_layout = QGridLayout()
        # Update scene json
        self.update_scene_button = QPushButton(
            language_wrapper.language_word_dict.get("scene_add_web")
        )
        self.update_scene_button.clicked.connect(self.update_scene_json)
        # Add to layout
        self.grid_layout.addWidget(self.opacity_label, 0, 0)
        self.grid_layout.addWidget(self.opacity_slider_value_label, 0, 1)
        self.grid_layout.addWidget(self.opacity_slider, 0, 2)
        self.grid_layout.addWidget(self.url_label, 1, 0)
        self.grid_layout.addWidget(self.web_url_input, 1, 1)
        self.grid_layout.addWidget(self.update_scene_button, 2, 0)
        self.setLayout(self.grid_layout)

    def opacity_trick(self) -> None:
        self.opacity_slider_value_label.setText(str(self.opacity_slider.value()))

    def update_scene_json(self):
        if self.web_url_input.text() == "" or self.web_url_input.text().strip() == "":
            message_box = QMessageBox(self)
            message_box.setText(
                language_wrapper.language_word_dict.get('not_prepare')
            )
            message_box.show()
        else:
            scene_json.update(
                {
                    f"{len(scene_json)}": {
                        "type": "WEB",
                        "url": self.web_url_input.text(),
                        "opacity": self.opacity_slider.value(),
                    }
                }
            )
            self.script_ui.renew_json_plain_text()
