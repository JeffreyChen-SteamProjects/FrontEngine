from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QSlider, QLabel, QLineEdit, QMessageBox, QPushButton

from frontengine.ui.page.scene_setting.scene_manager import SceneManagerUI
from frontengine.user_setting.scene_setting import scene_json
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class WebSceneSettingUI(QWidget):
    def __init__(self, script_ui: SceneManagerUI):
        front_engine_logger.info(f"[WebSceneSettingUI] Init | script_ui={script_ui}")
        super().__init__()
        self.script_ui = script_ui

        # Opacity setting
        self.opacity_label = QLabel(language_wrapper.language_word_dict.get("Opacity"))
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(1, 100)
        self.opacity_slider.setValue(20)
        self.opacity_slider_value_label = QLabel(str(self.opacity_slider.value()))
        self.opacity_slider.valueChanged.connect(self.opacity_trick)

        # WEB URL input
        self.url_label = QLabel(language_wrapper.language_word_dict.get("scene_url_label"))
        self.web_url_input = QLineEdit()

        # Update scene json
        self.update_scene_button = QPushButton(language_wrapper.language_word_dict.get("scene_add_web"))
        self.update_scene_button.clicked.connect(self.update_scene_json)

        # Layout
        self.grid_layout = QGridLayout(self)
        self.grid_layout.addWidget(self.opacity_label, 0, 0)
        self.grid_layout.addWidget(self.opacity_slider_value_label, 0, 1)
        self.grid_layout.addWidget(self.opacity_slider, 0, 2)
        self.grid_layout.addWidget(self.url_label, 1, 0)
        self.grid_layout.addWidget(self.web_url_input, 1, 1)
        self.grid_layout.addWidget(self.update_scene_button, 2, 0)

    def opacity_trick(self) -> None:
        front_engine_logger.info("[WebSceneSettingUI] opacity_trick")
        self.opacity_slider_value_label.setText(str(self.opacity_slider.value()))

    def update_scene_json(self) -> None:
        front_engine_logger.info("[WebSceneSettingUI] update_scene_json")
        if not self.web_url_input.text().strip():
            message_box = QMessageBox(self)
            message_box.setText(language_wrapper.language_word_dict.get("not_prepare"))
            message_box.exec()
            return

        scene_json[str(len(scene_json))] = {
            "type": "WEB",
            "url": self.web_url_input.text(),
            "opacity": self.opacity_slider.value(),
        }
        self.script_ui.renew_json_plain_text()
