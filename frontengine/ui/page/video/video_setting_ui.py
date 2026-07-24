from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QSlider, QLabel, QPushButton, QMessageBox, QCheckBox

from frontengine.show.video.video_player import VideoWidget
from frontengine.ui.dialog.choose_file_dialog import choose_video
from frontengine.ui.page.utils import (
    build_recent_combobox,
    build_target_monitor_combobox,
    coerce_int,
    dispatch_to_monitors,
    enable_file_drop,
    reload_recent_combobox,
    resolve_preferred_monitor,
    show_on_primary_screen,
    show_on_selected_monitor,
)
from frontengine.user_setting.user_setting_file import add_recent_file
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

        # Target monitor selector
        self.target_monitor_label = QLabel(
            language_wrapper.language_word_dict.get("target_monitor_label", "Target monitor")
        )
        self.target_monitor_combobox = build_target_monitor_combobox()

        # Recent files
        self.recent_files_label = QLabel(language_wrapper.language_word_dict.get("recent_files_label", "Recent"))
        self.recent_files_combobox = build_recent_combobox("video")
        self.recent_files_combobox.activated.connect(self._apply_recent_file)

        # Accept dropped video files
        self._drop_filter = enable_file_drop(self, (".mp4",), self._on_file_dropped)

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
        self.grid_layout.addWidget(self.target_monitor_label, 6, 0)
        self.grid_layout.addWidget(self.target_monitor_combobox, 6, 1)
        self.grid_layout.addWidget(self.recent_files_label, 7, 0)
        self.grid_layout.addWidget(self.recent_files_combobox, 7, 1)

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

        def present_on_monitor(widget: VideoWidget, monitor, index: int) -> None:
            # Mute secondary monitors when we duplicate audio across screens
            # to avoid the same track playing out of every output.
            if self.show_all_screen and index >= 1:
                widget.media_player.audioOutput().setVolume(0)
            show_on_selected_monitor(widget, self.fullscreen_checkbox, monitor)

        dispatch_to_monitors(
            parent=self,
            show_all_screen=self.show_all_screen,
            factory=lambda _monitor: self._create_video_widget(),
            present_primary=lambda widget: show_on_primary_screen(widget, self.fullscreen_checkbox),
            present_on_monitor=present_on_monitor,
            preferred_monitor_index=resolve_preferred_monitor(self.target_monitor_combobox),
        )

    def choose_and_copy_file_to_cwd_video_dir_then_play(self) -> None:
        front_engine_logger.info("[VideoSettingUI] choose_and_copy_file_to_cwd_video_dir_then_play")
        self.ready_label.setText(language_wrapper.language_word_dict.get("Not Ready"))
        self.ready_to_play = False
        self.video_path = choose_video(self)
        if self.video_path:
            self.ready_label.setText(language_wrapper.language_word_dict.get("Ready"))
            self.ready_to_play = True
            add_recent_file("video", self.video_path)
            reload_recent_combobox(self.recent_files_combobox, "video")

    def _apply_recent_file(self, _index: int = 0) -> None:
        path = self.recent_files_combobox.currentData()
        self.recent_files_combobox.setCurrentIndex(0)
        if not path:
            return
        front_engine_logger.info(f"[VideoSettingUI] _apply_recent_file | path={path}")
        self.video_path = path
        self.ready_to_play = True
        self.ready_label.setText(language_wrapper.language_word_dict.get("Ready"))

    def _on_file_dropped(self, path: str) -> None:
        front_engine_logger.info(f"[VideoSettingUI] _on_file_dropped | path={path}")
        self.video_path = path
        self.ready_to_play = True
        self.ready_label.setText(language_wrapper.language_word_dict.get("Ready"))
        add_recent_file("video", path)
        reload_recent_combobox(self.recent_files_combobox, "video")

    def opacity_trick(self) -> None:
        front_engine_logger.info("[VideoSettingUI] opacity_trick")
        self.opacity_slider_value_label.setText(str(self.opacity_slider.value()))

    def play_rate_trick(self) -> None:
        front_engine_logger.info("[VideoSettingUI] play_rate_trick")
        self.play_rate_slider_value_label.setText(str(self.play_rate_slider.value()))

    def volume_trick(self) -> None:
        front_engine_logger.info("[VideoSettingUI] volume_trick")
        self.volume_slider_value_label.setText(str(self.volume_slider.value()))

    def get_state(self) -> dict:
        return {
            "opacity": self.opacity_slider.value(),
            "play_rate": self.play_rate_slider.value(),
            "volume": self.volume_slider.value(),
            "video_path": self.video_path,
            "fullscreen": self.fullscreen_checkbox.isChecked(),
            "show_on_all_screen": self.show_on_all_screen_checkbox.isChecked(),
            "show_on_bottom": self.show_on_bottom_checkbox.isChecked(),
            "target_monitor": self.target_monitor_combobox.currentText(),
        }

    def set_state(self, state: dict) -> None:
        opacity = coerce_int(state.get("opacity"))
        if opacity is not None:
            self.opacity_slider.setValue(opacity)
        play_rate = coerce_int(state.get("play_rate"))
        if play_rate is not None:
            self.play_rate_slider.setValue(play_rate)
        volume = coerce_int(state.get("volume"))
        if volume is not None:
            self.volume_slider.setValue(volume)
        if state.get("video_path"):
            self.video_path = state["video_path"]
            self.ready_to_play = True
            self.ready_label.setText(language_wrapper.language_word_dict.get("Ready"))
        if "fullscreen" in state:
            self.fullscreen_checkbox.setChecked(bool(state["fullscreen"]))
        if "show_on_all_screen" in state:
            self.show_on_all_screen_checkbox.setChecked(bool(state["show_on_all_screen"]))
            self.show_all_screen = bool(state["show_on_all_screen"])
        if "show_on_bottom" in state:
            self.show_on_bottom_checkbox.setChecked(bool(state["show_on_bottom"]))
        if state.get("target_monitor") is not None:
            index = self.target_monitor_combobox.findText(str(state["target_monitor"]))
            if index >= 0:
                self.target_monitor_combobox.setCurrentIndex(index)