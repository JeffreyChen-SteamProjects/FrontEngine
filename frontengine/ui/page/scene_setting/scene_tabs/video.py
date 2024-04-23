from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QWidget, QBoxLayout, QPushButton, QSlider, QLabel, QHBoxLayout, QLineEdit
from frontengine.utils.multi_language.language_wrapper import language_wrapper

from frontengine.ui.dialog.choose_file_dialog import choose_video
from frontengine.ui.page.scene_setting.scene_tabs.tableview_model import add_row_data
from frontengine.utils.logging.loggin_instance import front_engine_logger


class VideoSceneSettingUI(QWidget):

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.box_layout = QBoxLayout(QBoxLayout.Direction.TopToBottom)
        # Video button
        self.video_button = QPushButton(
            language_wrapper.language_word_dict.get("scene_add_video")
        )
        self.video_button.clicked.connect(self.add_video)
        # Opacity slider
        self.opacity_slider = QSlider()
        self.opacity_slider.setMinimum(1)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setTickInterval(1)
        self.opacity_slider.setValue(20)
        self.opacity_slider.setOrientation(Qt.Orientation.Horizontal)
        self.opacity_label = QLabel()
        self.opacity_label.setText(language_wrapper.language_word_dict.get("Opacity"))
        self.opacity_box_h_layout = QHBoxLayout()
        self.opacity_box_h_layout.addWidget(self.opacity_label)
        self.opacity_box_h_layout.addWidget(self.opacity_slider)
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
        # Play rate slider
        self.play_rate_slider = QSlider()
        self.play_rate_slider.setMinimum(1)
        self.play_rate_slider.setMaximum(100)
        self.play_rate_slider.setTickInterval(1)
        self.play_rate_slider.setValue(100)
        self.play_rate_slider.setOrientation(Qt.Orientation.Horizontal)
        self.play_rate_label = QLabel()
        self.play_rate_label.setText(language_wrapper.language_word_dict.get("Play rate"))
        self.play_rate_h_layout = QHBoxLayout()
        self.play_rate_h_layout.addWidget(self.play_rate_label)
        self.play_rate_h_layout.addWidget(self.play_rate_slider)
        # Position x input
        self.position_x_input_label = QLabel(language_wrapper.language_word_dict.get("position_x"))
        self.position_x_input = QLineEdit()
        self.position_x_input.setValidator(QIntValidator(0, 999999, self))
        self.position_x_layout = QHBoxLayout()
        self.position_x_layout.addWidget(self.position_x_input_label)
        self.position_x_layout.addWidget(self.position_x_input)
        # Position y input
        self.position_y_input_label = QLabel(language_wrapper.language_word_dict.get("position_y"))
        self.position_y_input = QLineEdit()
        self.position_y_input.setValidator(QIntValidator(0, 999999, self))
        self.position_y_layout = QHBoxLayout()
        self.position_y_layout.addWidget(self.position_y_input_label)
        self.position_y_layout.addWidget(self.position_y_input)
        # Set UI
        self.box_layout.addLayout(self.opacity_box_h_layout)
        self.box_layout.addLayout(self.volume_box_h_layout)
        self.box_layout.addLayout(self.play_rate_h_layout)
        self.box_layout.addLayout(self.position_x_layout)
        self.box_layout.addLayout(self.position_y_layout)
        self.box_layout.addWidget(self.video_button)
        self.setLayout(self.box_layout)

    def add_video(self) -> None:
        video_path = choose_video(self)
        if video_path is not None:
            row_data = ["VIDEO", video_path, "", "", str(self.opacity_slider.value()), "",
                        str(self.volume_slider.value()), "", str(self.play_rate_slider.value()), "", "",
                        self.position_x_input.text(), self.position_y_input.text()]
            front_engine_logger.info(f"add video, param: {row_data}")
            add_row_data(row_data)
