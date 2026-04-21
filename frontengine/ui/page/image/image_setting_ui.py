from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QSlider, QLabel, QPushButton, QMessageBox, QCheckBox

from frontengine.show.image.paint_image import ImageWidget
from frontengine.ui.dialog.choose_file_dialog import choose_image
from frontengine.ui.page.utils import (
    build_target_monitor_combobox,
    dispatch_to_monitors,
    resolve_preferred_monitor,
    show_on_primary_screen,
    show_on_selected_monitor,
)
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class ImageSettingUI(QWidget):
    def __init__(self):
        front_engine_logger.info("[ImageSettingUI] Init")
        super().__init__()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # Init variable
        self.image_widget_list = []
        self.show_all_screen = False
        self.ready_to_play = False
        self.image_path: Optional[str] = None

        # Opacity setting
        self.opacity_label = QLabel(language_wrapper.language_word_dict.get("Opacity"))
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(1, 100)
        self.opacity_slider.setValue(20)
        self.opacity_slider_value_label = QLabel(str(self.opacity_slider.value()))
        self.opacity_slider.valueChanged.connect(self.opacity_trick)

        # Choose file button
        self.choose_file_button = QPushButton(language_wrapper.language_word_dict.get("image_setting_choose_file"))
        self.choose_file_button.clicked.connect(self.choose_and_copy_file_to_cwd_image_dir_then_play)

        # Ready label
        self.ready_label = QLabel(language_wrapper.language_word_dict.get("Not Ready"))

        # Start button
        self.start_button = QPushButton(language_wrapper.language_word_dict.get("image_setting_ui_play"))
        self.start_button.clicked.connect(self.start_play_image)

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
        self.grid_layout.addWidget(self.choose_file_button, 1, 0)
        self.grid_layout.addWidget(self.ready_label, 1, 1)
        self.grid_layout.addWidget(self.fullscreen_checkbox, 1, 2)
        self.grid_layout.addWidget(self.start_button, 2, 0)
        self.grid_layout.addWidget(self.show_on_all_screen_checkbox, 2, 1)
        self.grid_layout.addWidget(self.show_on_bottom_checkbox, 2, 2)
        self.grid_layout.addWidget(self.target_monitor_label, 3, 0)
        self.grid_layout.addWidget(self.target_monitor_combobox, 3, 1)

    def set_show_all_screen(self) -> None:
        front_engine_logger.info("[ImageSettingUI] set_show_all_screen")
        self.show_all_screen = self.show_on_all_screen_checkbox.isChecked()

    def _create_image_widget(self) -> ImageWidget:
        front_engine_logger.info("[ImageSettingUI] _create_image_widget")
        image_widget = ImageWidget(image_path=self.image_path)
        image_widget.set_ui_variable(opacity=float(self.opacity_slider.value()) / 100)
        image_widget.set_ui_window_flag(self.show_on_bottom_checkbox.isChecked())
        self.image_widget_list.append(image_widget)
        return image_widget

    def start_play_image(self) -> None:
        front_engine_logger.info("[ImageSettingUI] start_play_image")
        if not self.image_path or not self.ready_to_play:
            message_box = QMessageBox(self)
            message_box.setText(language_wrapper.language_word_dict.get("not_prepare"))
            message_box.exec()
            return

        dispatch_to_monitors(
            parent=self,
            show_all_screen=self.show_all_screen,
            factory=lambda _monitor: self._create_image_widget(),
            present_primary=lambda widget: show_on_primary_screen(widget, self.fullscreen_checkbox),
            present_on_monitor=lambda widget, monitor, _idx: show_on_selected_monitor(
                widget, self.fullscreen_checkbox, monitor
            ),
            preferred_monitor_index=resolve_preferred_monitor(self.target_monitor_combobox),
        )

    def choose_and_copy_file_to_cwd_image_dir_then_play(self) -> None:
        front_engine_logger.info("[ImageSettingUI] choose_and_copy_file_to_cwd_image_dir_then_play")
        self.ready_label.setText(language_wrapper.language_word_dict.get("Not Ready"))
        self.ready_to_play = False
        self.image_path = choose_image(self)
        if self.image_path:
            self.ready_label.setText(language_wrapper.language_word_dict.get("Ready"))
            self.ready_to_play = True

    def opacity_trick(self) -> None:
        front_engine_logger.info("[ImageSettingUI] opacity_trick")
        self.opacity_slider_value_label.setText(str(self.opacity_slider.value()))

    def get_state(self) -> dict:
        return {
            "opacity": self.opacity_slider.value(),
            "image_path": self.image_path,
            "fullscreen": self.fullscreen_checkbox.isChecked(),
            "show_on_all_screen": self.show_on_all_screen_checkbox.isChecked(),
            "show_on_bottom": self.show_on_bottom_checkbox.isChecked(),
            "target_monitor": self.target_monitor_combobox.currentText(),
        }

    def set_state(self, state: dict) -> None:
        if "opacity" in state:
            self.opacity_slider.setValue(int(state["opacity"]))
        if state.get("image_path"):
            self.image_path = state["image_path"]
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