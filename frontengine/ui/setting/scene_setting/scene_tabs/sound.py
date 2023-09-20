from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QBoxLayout, QSlider, QLabel, QHBoxLayout, QPushButton

from frontengine.ui.dialog.choose_file_dialog import choose_player_sound
from frontengine.ui.setting.scene_setting.scene_tabs.tableview_model import add_row_data
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class SoundSceneSettingUI(QWidget):

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.box_layout = QBoxLayout(QBoxLayout.Direction.TopToBottom)
        # Volume
        self.volume_slider = QSlider()
        self.volume_slider.setMinimum(1)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setTickInterval(1)
        self.volume_slider.setValue(100)
        self.volume_slider.setOrientation(Qt.Orientation.Horizontal)
        self.volume_label = QLabel()
        self.volume_label.setText(language_wrapper.language_word_dict.get("Volume"))
        self.volume_box_h_layout = QHBoxLayout()
        self.volume_box_h_layout.addWidget(self.volume_label)
        self.volume_box_h_layout.addWidget(self.volume_slider)
        # SOUND button
        self.sound_button = QPushButton(
            language_wrapper.language_word_dict.get("scene_add_sound")
        )
        self.sound_button.clicked.connect(self.add_sound)
        # Set UI
        self.box_layout.addLayout(self.volume_box_h_layout)
        self.box_layout.addWidget(self.sound_button)
        self.setLayout(self.box_layout)

    def add_sound(self) -> None:
        sound_path = choose_player_sound(self)
        if sound_path is not None:
            row_data = ["SOUND", sound_path, "", "", "", "", str(self.volume_slider.value()),
                        "", "", "", "", "", ""]
            front_engine_logger.info(f"add sound, param: {row_data}")
            add_row_data(row_data)
