from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QPushButton, QSlider, QMessageBox

from frontengine.ui.dialog.choose_file_dialog import choose_player_sound
from frontengine.ui.page.scene_setting.scene_manager import SceneManagerUI
from frontengine.user_setting.scene_setting import scene_json
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class SoundSceneSettingUI(QWidget):

    def __init__(self, script_ui: SceneManagerUI):
        front_engine_logger.info(f"Init SoundSceneSettingUI script_ui: {script_ui}")
        super().__init__()
        self.script_ui = script_ui
        self.ready_to_play = False
        # Volume setting
        self.volume_label = QLabel(
            language_wrapper.language_word_dict.get("Volume")
        )
        self.volume_slider = QSlider()
        self.volume_slider.setMinimum(1)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setTickInterval(1)
        self.volume_slider.setValue(100)
        self.volume_slider_value_label = QLabel(str(self.volume_slider.value()))
        self.volume_slider.setOrientation(Qt.Orientation.Horizontal)
        self.volume_slider.actionTriggered.connect(self.volume_trick)
        # Choose file button
        self.player_sound_path: [str, None] = None
        # Choose file button
        self.choose_player_file_button = QPushButton(
            language_wrapper.language_word_dict.get("sound_player_setting_choose_sound_file")
        )
        self.choose_player_file_button.clicked.connect(self.get_sound)
        # Ready label and variable
        self.player_ready_label = QLabel(
            language_wrapper.language_word_dict.get("Not Ready")
        )
        self.update_scene_button = QPushButton(
            language_wrapper.language_word_dict.get("scene_add_sound")
        )
        self.update_scene_button.clicked.connect(self.update_scene_json)
        self.grid_layout = QGridLayout()
        self.grid_layout.addWidget(self.volume_label, 0, 0)
        self.grid_layout.addWidget(self.volume_slider_value_label, 0, 1)
        self.grid_layout.addWidget(self.volume_slider, 0, 2)
        self.grid_layout.addWidget(self.choose_player_file_button, 1, 0)
        self.grid_layout.addWidget(self.player_ready_label, 1, 1)
        self.grid_layout.addWidget(self.update_scene_button, 2, 0)
        self.setLayout(self.grid_layout)

    def volume_trick(self) -> None:
        front_engine_logger.info("SoundSceneSettingUI volume_trick")
        self.volume_slider_value_label.setText(str(self.volume_slider.value()))

    def get_sound(self) -> None:
        front_engine_logger.info("SoundSceneSettingUI get_sound")
        self.player_ready_label.setText(
            language_wrapper.language_word_dict.get("Not Ready")
        )
        self.ready_to_play = False
        self.player_sound_path = choose_player_sound(self)
        if self.player_sound_path is not None:
            self.player_ready_label.setText(
                language_wrapper.language_word_dict.get("Ready")
            )
            self.ready_to_play = True

    def update_scene_json(self):
        front_engine_logger.info("SoundSceneSettingUI update_scene_json")
        if self.player_sound_path is None:
            message_box = QMessageBox(self)
            message_box.setText(
                language_wrapper.language_word_dict.get('not_prepare')
            )
            message_box.show()
        else:
            scene_json.update(
                {
                    f"{len(scene_json)}": {
                        "type": "SOUND",
                        "file_path": self.player_sound_path,
                        "volume": self.volume_slider.value()
                    }
                }
            )
            self.script_ui.renew_json_plain_text()
