from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QSlider, QPushButton, QMessageBox

from frontengine.ui.dialog.choose_file_dialog import choose_video
from frontengine.ui.page.scene_setting.scene_manager import SceneManagerUI
from frontengine.user_setting.scene_setting import scene_json
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class VideoSceneSettingUI(QWidget):

    def __init__(self, script_ui: SceneManagerUI):
        super().__init__()
        self.script_ui = script_ui
        self.ready_to_play = False
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
        # Play rate setting
        self.play_rate_label = QLabel(
            language_wrapper.language_word_dict.get("Play rate")
        )
        self.play_rate_slider = QSlider()
        self.play_rate_slider.setMinimum(1)
        self.play_rate_slider.setMaximum(200)
        self.play_rate_slider.setTickInterval(1)
        self.play_rate_slider.setValue(100)
        self.play_rate_slider_value_label = QLabel(str(self.play_rate_slider.value()))
        self.play_rate_slider.setOrientation(Qt.Orientation.Horizontal)
        self.play_rate_slider.actionTriggered.connect(self.play_rate_trick)
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
        # Ready label and variable
        self.ready_label = QLabel(
            language_wrapper.language_word_dict.get("Not Ready")
        )
        # Choose video file
        self.choose_file_button = QPushButton(
            language_wrapper.language_word_dict.get("video_setting_choose_file")
        )
        self.choose_file_button.clicked.connect(self.get_video)
        # Update scene json
        self.update_scene_button = QPushButton(
            language_wrapper.language_word_dict.get("scene_add_video")
        )
        self.update_scene_button.clicked.connect(self.update_scene_json)
        self.video_path: [str, None] = None
        self.grid_layout = QGridLayout()
        self.grid_layout.addWidget(self.opacity_label, 0, 0)
        self.grid_layout.addWidget(self.opacity_slider_value_label, 0, 1)
        self.grid_layout.addWidget(self.opacity_slider, 0, 2)
        self.grid_layout.addWidget(self.play_rate_label, 1, 0)
        self.grid_layout.addWidget(self.play_rate_slider_value_label, 1, 1)
        self.grid_layout.addWidget(self.play_rate_slider, 1, 2)
        self.grid_layout.addWidget(self.volume_label, 2, 0)
        self.grid_layout.addWidget(self.volume_slider_value_label, 2, 1)
        self.grid_layout.addWidget(self.volume_slider, 2, 2)
        self.grid_layout.addWidget(self.choose_file_button, 3, 0)
        self.grid_layout.addWidget(self.ready_label, 3, 1)
        self.grid_layout.addWidget(self.update_scene_button, 4, 0)
        self.setLayout(self.grid_layout)

    def get_video(self) -> None:
        self.ready_label.setText(
            language_wrapper.language_word_dict.get("Not Ready")
        )
        self.ready_to_play = False
        self.video_path = choose_video(self)
        if self.video_path is not None:
            self.ready_label.setText(
                language_wrapper.language_word_dict.get("Ready")
            )
            self.ready_to_play = True

    def opacity_trick(self) -> None:
        self.opacity_slider_value_label.setText(str(self.opacity_slider.value()))

    def play_rate_trick(self) -> None:
        self.play_rate_slider_value_label.setText(str(self.play_rate_slider.value()))

    def volume_trick(self) -> None:
        self.volume_slider_value_label.setText(str(self.volume_slider.value()))

    def update_scene_json(self):
        if self.video_path is None:
            message_box = QMessageBox(self)
            message_box.setText(
                language_wrapper.language_word_dict.get('not_prepare')
            )
            message_box.show()
        else:
            scene_json.update(
                {
                    f"{len(scene_json)}": {
                        "type": "VIDEO",
                        "file_path": self.video_path,
                        "opacity": self.opacity_slider.value(),
                        "volume": self.volume_slider.value(),
                        "play_rate": self.play_rate_slider.value()
                    }
                }
            )
            self.script_ui.renew_json_plain_text()
