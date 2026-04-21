from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QSlider, QPushButton, QMessageBox, QCheckBox

from frontengine.show.gif.paint_gif import GifWidget
from frontengine.ui.dialog.choose_file_dialog import choose_gif
from frontengine.ui.page.utils import (
    build_target_monitor_combobox,
    dispatch_to_monitors,
    resolve_preferred_monitor,
    show_on_primary_screen,
    show_on_selected_monitor,
)
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class GIFSettingUI(QWidget):
    def __init__(self):
        front_engine_logger.info("[GIFSettingUI] Init")
        super().__init__()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # Init variable
        self.gif_widget_list = []
        self.show_all_screen = False
        self.ready_to_play = False
        self.gif_image_path: Optional[str] = None

        # Opacity setting
        self.opacity_label = QLabel(language_wrapper.language_word_dict.get("Opacity"))
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(1, 100)
        self.opacity_slider.setValue(20)
        self.opacity_slider_value_label = QLabel(str(self.opacity_slider.value()))
        self.opacity_slider.valueChanged.connect(self.opacity_trick)

        # Speed setting
        self.speed_label = QLabel(language_wrapper.language_word_dict.get("Speed"))
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 200)
        self.speed_slider.setValue(100)
        self.speed_slider_value_label = QLabel(str(self.speed_slider.value()))
        self.speed_slider.valueChanged.connect(self.speed_trick)

        # Choose file button
        self.choose_file_button = QPushButton(language_wrapper.language_word_dict.get("gif_setting_ui_choose_file"))
        self.choose_file_button.clicked.connect(self.choose_and_copy_file_to_cwd_gif_dir_then_play)

        # Ready label
        self.ready_label = QLabel(language_wrapper.language_word_dict.get("Not Ready"))

        # Start button
        self.start_button = QPushButton(language_wrapper.language_word_dict.get("gif_setting_ui_play"))
        self.start_button.clicked.connect(self.start_play_gif)

        # Checkboxes
        self.fullscreen_checkbox = QCheckBox(language_wrapper.language_word_dict.get("fullscreen_checkbox_label"))
        self.fullscreen_checkbox.setChecked(True)

        self.show_on_all_screen_checkbox = QCheckBox(language_wrapper.language_word_dict.get("Show on all screen"))
        self.show_on_all_screen_checkbox.clicked.connect(self.set_show_all_screen)

        self.show_on_bottom_checkbox = QCheckBox(language_wrapper.language_word_dict.get("Show on bottom"))

        # Target monitor selector
        self.target_monitor_label = QLabel(
            language_wrapper.language_word_dict.get("target_monitor_label", "Target monitor")
        )
        self.target_monitor_combobox = build_target_monitor_combobox()

        # Layout
        self.grid_layout.addWidget(self.opacity_label, 0, 0)
        self.grid_layout.addWidget(self.opacity_slider_value_label, 0, 1)
        self.grid_layout.addWidget(self.opacity_slider, 0, 2)
        self.grid_layout.addWidget(self.speed_label, 1, 0)
        self.grid_layout.addWidget(self.speed_slider_value_label, 1, 1)
        self.grid_layout.addWidget(self.speed_slider, 1, 2)
        self.grid_layout.addWidget(self.choose_file_button, 2, 0)
        self.grid_layout.addWidget(self.ready_label, 2, 1)
        self.grid_layout.addWidget(self.fullscreen_checkbox, 2, 2)
        self.grid_layout.addWidget(self.start_button, 3, 0)
        self.grid_layout.addWidget(self.show_on_all_screen_checkbox, 3, 1)
        self.grid_layout.addWidget(self.show_on_bottom_checkbox, 3, 2)
        self.grid_layout.addWidget(self.target_monitor_label, 4, 0)
        self.grid_layout.addWidget(self.target_monitor_combobox, 4, 1)

    def set_show_all_screen(self) -> None:
        front_engine_logger.info("[GIFSettingUI] set_show_all_screen")
        self.show_all_screen = self.show_on_all_screen_checkbox.isChecked()

    def _create_gif_widget(self) -> GifWidget:
        front_engine_logger.info("[GIFSettingUI] _create_gif_widget")
        gif_widget = GifWidget(gif_image_path=self.gif_image_path)
        gif_widget.set_gif_variable(speed=self.speed_slider.value())
        gif_widget.set_ui_variable(opacity=float(self.opacity_slider.value()) / 100)
        gif_widget.set_ui_window_flag(show_on_bottom=self.show_on_bottom_checkbox.isChecked())
        self.gif_widget_list.append(gif_widget)
        return gif_widget

    def start_play_gif(self) -> None:
        front_engine_logger.info("[GIFSettingUI] start_play_gif")
        if not self.gif_image_path or not self.ready_to_play:
            message_box = QMessageBox(self)
            message_box.setText(language_wrapper.language_word_dict.get("not_prepare"))
            message_box.exec()
            return

        dispatch_to_monitors(
            parent=self,
            show_all_screen=self.show_all_screen,
            factory=lambda _monitor: self._create_gif_widget(),
            present_primary=lambda widget: show_on_primary_screen(widget, self.fullscreen_checkbox),
            present_on_monitor=lambda widget, monitor, _idx: show_on_selected_monitor(
                widget, self.fullscreen_checkbox, monitor
            ),
            preferred_monitor_index=resolve_preferred_monitor(self.target_monitor_combobox),
        )

    def choose_and_copy_file_to_cwd_gif_dir_then_play(self) -> None:
        front_engine_logger.info("[GIFSettingUI] choose_and_copy_file_to_cwd_gif_dir_then_play")
        self.ready_label.setText(language_wrapper.language_word_dict.get("Not Ready"))
        self.ready_to_play = False
        self.gif_image_path = choose_gif(self)
        if self.gif_image_path:
            self.ready_label.setText(language_wrapper.language_word_dict.get("Ready"))
            self.ready_to_play = True

    def opacity_trick(self) -> None:
        front_engine_logger.info("[GIFSettingUI] opacity_trick")
        self.opacity_slider_value_label.setText(str(self.opacity_slider.value()))

    def speed_trick(self) -> None:
        front_engine_logger.info("[GIFSettingUI] speed_trick")
        self.speed_slider_value_label.setText(str(self.speed_slider.value()))

    def get_state(self) -> dict:
        return {
            "opacity": self.opacity_slider.value(),
            "speed": self.speed_slider.value(),
            "gif_image_path": self.gif_image_path,
            "fullscreen": self.fullscreen_checkbox.isChecked(),
            "show_on_all_screen": self.show_on_all_screen_checkbox.isChecked(),
            "show_on_bottom": self.show_on_bottom_checkbox.isChecked(),
            "target_monitor": self.target_monitor_combobox.currentText(),
        }

    def set_state(self, state: dict) -> None:
        if "opacity" in state:
            self.opacity_slider.setValue(int(state["opacity"]))
        if "speed" in state:
            self.speed_slider.setValue(int(state["speed"]))
        if state.get("gif_image_path"):
            self.gif_image_path = state["gif_image_path"]
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