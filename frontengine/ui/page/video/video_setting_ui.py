from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget, QGridLayout, QSlider, QLabel, QPushButton, QMessageBox, QCheckBox, QDialog

from frontengine.show.video.video_player import VideoWidget
from frontengine.ui.dialog.choose_file_dialog import choose_video
from frontengine.ui.page.utils import create_monitor_selection_dialog, show_on_selected_monitor, show_on_primary_screen
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class VideoSettingUI(QWidget):
    def __init__(self):
        front_engine_logger.info("[VideoSettingUI] Init")
        super().__init__()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        # Init variable
        self.video_widget_list = []
        self.show_all_screen = False
        self.ready_to_play = False
        self.video_path: Optional[str] = None

        # Opacity setting
        self.opacity_label = QLabel(language_wrapper.language_word_dict.get("Opacity"))
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(1, 100)
        self.opacity_slider.setValue(20)
        self.opacity_slider_value_label = QLabel(str(self.opacity_slider.value()))
        self.opacity_slider.valueChanged.connect(self.opacity_trick)

        # Play rate setting
        self.play_rate_label = QLabel(language_wrapper.language_word_dict.get("Play rate"))
        self.play_rate_slider = QSlider(Qt.Orientation.Horizontal)
        self.play_rate_slider.setRange(1, 200)
        self.play_rate_slider.setValue(100)
        self.play_rate_slider_value_label = QLabel(str(self.play_rate_slider.value()))
        self.play_rate_slider.valueChanged.connect(self.play_rate_trick)

        # Volume setting
        self.volume_label = QLabel(language_wrapper.language_word_dict.get("Volume"))
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(1, 100)
        self.volume_slider.setValue(100)
        self.volume_slider_value_label = QLabel(str(self.volume_slider.value()))
        self.volume_slider.valueChanged.connect(self.volume_trick)

        # Ready label
        self.ready_label = QLabel(language_wrapper.language_word_dict.get("Not Ready"))

        # Choose file button
        self.choose_file_button = QPushButton(language_wrapper.language_word_dict.get("video_setting_choose_file"))
        self.choose_file_button.clicked.connect(self.choose_and_copy_file_to_cwd_video_dir_then_play)

        # Start button
        self.start_button = QPushButton(language_wrapper.language_word_dict.get("video_setting_start_play"))
        self.start_button.clicked.connect(self.start_play_video)

        # Expand
        self.fullscreen_checkbox = QCheckBox(language_wrapper.language_word_dict.get("fullscreen_checkbox_label"))
        self.fullscreen_checkbox.setChecked(True)

        # Show on all screen
        self.show_on_all_screen_checkbox = QCheckBox(language_wrapper.language_word_dict.get("Show on all screen"))
        self.show_on_all_screen_checkbox.clicked.connect(self.set_show_all_screen)

        # Show on bottom
        self.show_on_bottom_checkbox = QCheckBox(language_wrapper.language_word_dict.get("Show on bottom"))

        # Layout
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
        self.grid_layout.addWidget(self.fullscreen_checkbox, 4, 2)
        self.grid_layout.addWidget(self.start_button, 5, 0)
        self.grid_layout.addWidget(self.ready_label, 5, 1)

    def set_show_all_screen(self) -> None:
        front_engine_logger.info("[VideoSettingUI] set_show_all_screen")
        self.show_all_screen = self.show_on_all_screen_checkbox.isChecked()

    def _create_video_widget(self) -> VideoWidget:
        front_engine_logger.info("[VideoSettingUI] _create_video_widget")
        video_widget = VideoWidget(video_path=self.video_path)
        video_widget.set_ui_variable(opacity=float(self.opacity_slider.value()) / 100)
        video_widget.set_player_variable(
            play_rate=float(self.play_rate_slider.value()) / 100,
            volume=float(self.volume_slider.value()) / 100
        )
        video_widget.set_ui_window_flag(self.show_on_bottom_checkbox.isChecked())
        self.video_widget_list.append(video_widget)
        return video_widget

    def start_play_video(self) -> None:
        if not self.video_path or not self.ready_to_play:
            message_box = QMessageBox(self)
            message_box.setText(language_wrapper.language_word_dict.get("not_prepare"))
            message_box.exec()
            return

        front_engine_logger.info("[VideoSettingUI] start_play_video")
        monitors = QGuiApplication.screens()

        if not self.show_all_screen and len(monitors) <= 1:
            video_widget = self._create_video_widget()
            show_on_primary_screen(video_widget, self.fullscreen_checkbox)

        elif not self.show_all_screen and len(monitors) >= 2:
            input_dialog, combobox = create_monitor_selection_dialog(self, monitors)
            result = input_dialog.exec()
            if result == QDialog.DialogCode.Accepted:
                select_monitor_index = int(combobox.currentText())
                if len(monitors) > select_monitor_index:
                    monitor = monitors[select_monitor_index]
                    video_widget = self._create_video_widget()
                    show_on_selected_monitor(video_widget, self.fullscreen_checkbox, monitor)

        else:
            for count, monitor in enumerate(monitors):
                video_widget = self._create_video_widget()
                if count >= 1:
                    video_widget.media_player.audioOutput().setVolume(0)
                show_on_selected_monitor(video_widget, self.fullscreen_checkbox, monitor)

    def choose_and_copy_file_to_cwd_video_dir_then_play(self) -> None:
        front_engine_logger.info("[VideoSettingUI] choose_and_copy_file_to_cwd_video_dir_then_play")
        self.ready_label.setText(language_wrapper.language_word_dict.get("Not Ready"))
        self.ready_to_play = False
        self.video_path = choose_video(self)
        if self.video_path:
            self.ready_label.setText(language_wrapper.language_word_dict.get("Ready"))
            self.ready_to_play = True

    def opacity_trick(self) -> None:
        front_engine_logger.info("[VideoSettingUI] opacity_trick")
        self.opacity_slider_value_label.setText(str(self.opacity_slider.value()))

    def play_rate_trick(self) -> None:
        front_engine_logger.info("[VideoSettingUI] play_rate_trick")
        self.play_rate_slider_value_label.setText(str(self.play_rate_slider.value()))

    def volume_trick(self) -> None:
        front_engine_logger.info("[VideoSettingUI] volume_trick")
        self.volume_slider_value_label.setText(str(self.volume_slider.value()))