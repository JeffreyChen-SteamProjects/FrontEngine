from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QSlider, QLabel, QPushButton, QMessageBox

from frontengine.ui.dialog.choose_file_dialog import choose_gif
from frontengine.ui.page.scene_setting.scene_manager import SceneManagerUI
from frontengine.user_setting.scene_setting import scene_json
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class GIFSceneSettingUI(QWidget):
    def __init__(self, script_ui: SceneManagerUI):
        front_engine_logger.info(f"[GIFSceneSettingUI] Init | script_ui={script_ui}")
        super().__init__()
        self.script_ui = script_ui

        # UI components
        self.opacity_label = QLabel(language_wrapper.language_word_dict.get("Opacity"))
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(1, 100)
        self.opacity_slider.setValue(20)
        self.opacity_slider_value_label = QLabel(str(self.opacity_slider.value()))
        self.opacity_slider.valueChanged.connect(self.opacity_trick)

        self.speed_label = QLabel(language_wrapper.language_word_dict.get("Speed"))
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 200)
        self.speed_slider.setValue(100)
        self.speed_slider_value_label = QLabel(str(self.speed_slider.value()))
        self.speed_slider.valueChanged.connect(self.speed_trick)

        self.choose_file_button = QPushButton(language_wrapper.language_word_dict.get("gif_setting_ui_choose_file"))
        self.choose_file_button.clicked.connect(self.get_gif)

        self.ready_to_play = False
        self.ready_label = QLabel(language_wrapper.language_word_dict.get("Not Ready"))
        self.gif_image_path: Optional[str] = None

        self.update_scene_button = QPushButton(language_wrapper.language_word_dict.get("scene_add_gif"))
        self.update_scene_button.clicked.connect(self.update_scene_json)

        # Layout
        self.grid_layout = QGridLayout(self)
        self.grid_layout.addWidget(self.opacity_label, 0, 0)
        self.grid_layout.addWidget(self.opacity_slider_value_label, 0, 1)
        self.grid_layout.addWidget(self.opacity_slider, 0, 2)
        self.grid_layout.addWidget(self.speed_label, 1, 0)
        self.grid_layout.addWidget(self.speed_slider_value_label, 1, 1)
        self.grid_layout.addWidget(self.speed_slider, 1, 2)
        self.grid_layout.addWidget(self.choose_file_button, 2, 0)
        self.grid_layout.addWidget(self.ready_label, 2, 1)
        self.grid_layout.addWidget(self.update_scene_button, 3, 0)

    def opacity_trick(self) -> None:
        front_engine_logger.info("[GIFSceneSettingUI] opacity_trick")
        self.opacity_slider_value_label.setText(str(self.opacity_slider.value()))

    def speed_trick(self) -> None:
        front_engine_logger.info("[GIFSceneSettingUI] speed_trick")
        self.speed_slider_value_label.setText(str(self.speed_slider.value()))

    def get_gif(self) -> None:
        front_engine_logger.info("[GIFSceneSettingUI] get_gif")
        self.ready_label.setText(language_wrapper.language_word_dict.get("Not Ready"))
        self.ready_to_play = False
        self.gif_image_path = choose_gif(self)
        if self.gif_image_path:
            self.ready_label.setText(language_wrapper.language_word_dict.get("Ready"))
            self.ready_to_play = True

    def update_scene_json(self) -> None:
        front_engine_logger.info("[GIFSceneSettingUI] update_scene_json")
        if not self.gif_image_path:
            message_box = QMessageBox(self)
            message_box.setText(language_wrapper.language_word_dict.get("not_prepare"))
            message_box.exec()
            return

        scene_json[str(len(scene_json))] = {
            "type": "GIF",
            "file_path": self.gif_image_path,
            "opacity": self.opacity_slider.value(),
            "speed": self.speed_slider.value()
        }
        self.script_ui.renew_json_plain_text()
