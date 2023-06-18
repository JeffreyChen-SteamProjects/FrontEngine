import os
import shutil
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QScreen
from PySide6.QtWidgets import QWidget, QGridLayout, QSlider, QLabel, QPushButton, QMessageBox, QFileDialog, \
    QCheckBox

from frontengine.show.video.video_player import VideoWidget
from frontengine.ui.setting.choose_dialog.choose_file_dialog import choose_video
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class VideoSettingUI(QWidget):

    def __init__(self):
        super().__init__()
        self.grid_layout = QGridLayout()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        # Init variable
        self.video_widget_list = list()
        self.show_all_screen = False
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
        self.video_path: [str, None] = None
        # Choose file button
        self.choose_file_button = QPushButton(
            language_wrapper.language_word_dict.get("video_setting_choose_file")
        )
        self.choose_file_button.clicked.connect(self.choose_and_copy_file_to_cwd_gif_dir_then_play)
        # Start button
        self.start_button = QPushButton(
            language_wrapper.language_word_dict.get("video_setting_start_play")
        )
        self.start_button.clicked.connect(self.start_play_gif)
        # Show on all screen
        self.show_on_all_screen_checkbox = QCheckBox(
            language_wrapper.language_word_dict.get("Show on all screen")
        )
        self.show_on_all_screen_checkbox.clicked.connect(self.set_show_all_screen)
        # Show on bottom
        self.show_on_bottom_checkbox = QCheckBox(
            language_wrapper.language_word_dict.get("Show on bottom")
        )
        # Add to layout
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
        self.grid_layout.addWidget(self.show_on_all_screen_checkbox, 4, 0)
        self.grid_layout.addWidget(self.show_on_bottom_checkbox, 4, 1)
        self.grid_layout.addWidget(self.start_button, 5, 0)
        self.grid_layout.addWidget(self.ready_label, 5, 1)
        self.setLayout(self.grid_layout)

    def set_show_all_screen(self) -> None:
        self.show_all_screen = self.show_on_all_screen_checkbox.isChecked()

    def _create_video_widget(self) -> VideoWidget:
        video_widget = VideoWidget(video_path=self.video_path)
        video_widget.set_ui_variable(opacity=float(self.opacity_slider.value()) / 100)
        video_widget.set_player_variable(
            play_rate=float(self.play_rate_slider.value()) / 100,
            volume=float(self.volume_slider.value() / 100)
        )
        video_widget.set_ui_window_flag(self.show_on_bottom_checkbox.isChecked())
        self.video_widget_list.append(video_widget)
        return video_widget

    def start_play_gif(self) -> None:
        if self.video_path is None or self.ready_to_play is False:
            message_box = QMessageBox(self)
            message_box.setText(
                language_wrapper.language_word_dict.get("not_prepare")
            )
            message_box.show()
        else:
            front_engine_logger.info("start_play_gif")
            if self.show_all_screen:
                video_widget = self._create_video_widget()
                video_widget.set_ui_window_flag(self.show_on_bottom_checkbox.isChecked())
                video_widget.showMaximized()
            else:
                monitors = QScreen.virtualSiblings(self.screen())
                for screen in monitors:
                    monitor = screen.availableGeometry()
                    video_widget = self._create_video_widget()
                    video_widget.move(monitor.left(), monitor.top())
                    video_widget.showMaximized()

    def choose_and_copy_file_to_cwd_gif_dir_then_play(self) -> None:
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
