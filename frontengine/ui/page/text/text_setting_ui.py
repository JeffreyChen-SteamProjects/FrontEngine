from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QGridLayout, QSlider, QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox, \
    QFontComboBox, QMessageBox

from frontengine.show.text.draw_text import TextWidget
from frontengine.ui.page.utils import (
    build_target_monitor_combobox,
    coerce_int,
    dispatch_to_monitors,
    resolve_preferred_monitor,
)
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper

# 名稱 -> HEX 顏色 / Named text colors -> hex
_TEXT_COLORS = [
    ("Black", "#000000"), ("White", "#ffffff"), ("Red", "#ff0000"),
    ("Green", "#00ff00"), ("Blue", "#0000ff"), ("Yellow", "#ffff00"),
    ("Cyan", "#00ffff"), ("Magenta", "#ff00ff"),
]


class TextSettingUI(QWidget):
    def __init__(self):
        front_engine_logger.info("[TextSettingUI] Init")
        super().__init__()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        # Init variable
        self.text_widget_list = []
        self.show_all_screen = False

        # Opacity setting
        self.opacity_label = QLabel(language_wrapper.language_word_dict.get("Opacity"))
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(1, 100)
        self.opacity_slider.setValue(20)
        self.opacity_slider_value_label = QLabel(str(self.opacity_slider.value()))
        self.opacity_slider.valueChanged.connect(self.opacity_trick)

        # Font size setting
        self.font_size_label = QLabel(language_wrapper.language_word_dict.get("Font size"))
        self.font_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_size_slider.setRange(1, 600)
        self.font_size_slider.setValue(100)
        self.font_size_slider_value_label = QLabel(str(self.font_size_slider.value()))
        self.font_size_slider.valueChanged.connect(self.font_size_trick)

        # Text input
        self.line_edit = QLineEdit()

        # Start Button
        self.start_button = QPushButton(language_wrapper.language_word_dict.get("text_setting_start_draw"))
        self.start_button.clicked.connect(self.start_draw_text_on_screen)

        # Show on all screen
        self.show_on_all_screen_checkbox = QCheckBox(language_wrapper.language_word_dict.get("Show on all screen"))
        self.show_on_all_screen_checkbox.clicked.connect(self.set_show_all_screen)

        # Show on bottom
        self.show_on_bottom_checkbox = QCheckBox(language_wrapper.language_word_dict.get("Show on bottom"))

        # Text position
        self.text_position_label = QLabel(language_wrapper.language_word_dict.get("text_setting_choose_alignment"))
        self.text_position_combobox = QComboBox()
        self.text_position_combobox.addItems(["TopLeft", "TopRight", "BottomLeft", "BottomRight", "Center"])

        # Text color
        self.text_color_label = QLabel(language_wrapper.language_word_dict.get("text_color_label", "Color"))
        self.text_color_combobox = QComboBox()
        for name, hex_value in _TEXT_COLORS:
            self.text_color_combobox.addItem(name, hex_value)

        # Font family
        self.font_family_label = QLabel(language_wrapper.language_word_dict.get("font_family_label", "Font"))
        self.font_family_combobox = QFontComboBox()

        # Marquee scroll
        self.marquee_checkbox = QCheckBox(language_wrapper.language_word_dict.get("marquee_label", "Marquee"))
        self.marquee_speed_label = QLabel(language_wrapper.language_word_dict.get("marquee_speed_label", "Speed"))
        self.marquee_speed_combobox = QComboBox()
        self.marquee_speed_combobox.addItems(["2", "4", "6", "8", "12"])
        self.marquee_speed_combobox.setCurrentText("4")

        # Outline (readability on any background)
        self.outline_checkbox = QCheckBox(language_wrapper.language_word_dict.get("outline_label", "Outline"))
        self.outline_color_combobox = QComboBox()
        for name, hex_value in _TEXT_COLORS:
            self.outline_color_combobox.addItem(name, hex_value)
        self.outline_color_combobox.setCurrentText("White")

        # Target monitor selector
        self.target_monitor_label = QLabel(
            language_wrapper.language_word_dict.get("target_monitor_label", "Target monitor")
        )
        self.target_monitor_combobox = build_target_monitor_combobox()

        # Layout
        self.grid_layout.addWidget(self.opacity_label, 0, 0)
        self.grid_layout.addWidget(self.opacity_slider_value_label, 0, 1)
        self.grid_layout.addWidget(self.opacity_slider, 0, 2)
        self.grid_layout.addWidget(self.font_size_label, 1, 0)
        self.grid_layout.addWidget(self.font_size_slider_value_label, 1, 1)
        self.grid_layout.addWidget(self.font_size_slider, 1, 2)
        self.grid_layout.addWidget(self.show_on_all_screen_checkbox, 2, 0)
        self.grid_layout.addWidget(self.show_on_bottom_checkbox, 2, 1)
        self.grid_layout.addWidget(self.text_position_label, 3, 0)
        self.grid_layout.addWidget(self.text_position_combobox, 3, 1)
        self.grid_layout.addWidget(self.start_button, 4, 0)
        self.grid_layout.addWidget(self.line_edit, 4, 1)
        self.grid_layout.addWidget(self.target_monitor_label, 5, 0)
        self.grid_layout.addWidget(self.target_monitor_combobox, 5, 1)
        self.grid_layout.addWidget(self.text_color_label, 6, 0)
        self.grid_layout.addWidget(self.text_color_combobox, 6, 1)
        self.grid_layout.addWidget(self.font_family_label, 7, 0)
        self.grid_layout.addWidget(self.font_family_combobox, 7, 1)
        self.grid_layout.addWidget(self.marquee_checkbox, 8, 0)
        self.grid_layout.addWidget(self.marquee_speed_label, 8, 1)
        self.grid_layout.addWidget(self.marquee_speed_combobox, 8, 2)
        self.grid_layout.addWidget(self.outline_checkbox, 9, 0)
        self.grid_layout.addWidget(self.outline_color_combobox, 9, 1)

    def set_show_all_screen(self) -> None:
        front_engine_logger.info("[TextSettingUI] set_show_all_screen")
        self.show_all_screen = self.show_on_all_screen_checkbox.isChecked()

    def _create_text_widget(self) -> TextWidget:
        front_engine_logger.info("[TextSettingUI] _create_text_widget")
        text_widget = TextWidget(
            text=self.line_edit.text(),
            alignment=self.text_position_combobox.currentText()
        )
        text_widget.set_font_variable(self.font_size_slider.value())
        text_widget.set_font_family(self.font_family_combobox.currentFont().family())
        text_widget.set_color(self.text_color_combobox.currentData())
        text_widget.set_outline(
            self.outline_checkbox.isChecked(), self.outline_color_combobox.currentData()
        )
        text_widget.set_ui_variable(float(self.opacity_slider.value()) / 100)
        text_widget.set_ui_window_flag(self.show_on_bottom_checkbox.isChecked())
        text_widget.set_marquee(
            self.marquee_checkbox.isChecked(),
            int(self.marquee_speed_combobox.currentText()),
        )
        self.text_widget_list.append(text_widget)
        return text_widget

    def opacity_trick(self) -> None:
        front_engine_logger.info("[TextSettingUI] opacity_trick")
        self.opacity_slider_value_label.setText(str(self.opacity_slider.value()))

    def font_size_trick(self) -> None:
        front_engine_logger.info("[TextSettingUI] font_size_trick")
        self.font_size_slider_value_label.setText(str(self.font_size_slider.value()))

    def get_state(self) -> dict:
        return {
            "opacity": self.opacity_slider.value(),
            "font_size": self.font_size_slider.value(),
            "text": self.line_edit.text(),
            "alignment": self.text_position_combobox.currentText(),
            "show_on_all_screen": self.show_on_all_screen_checkbox.isChecked(),
            "show_on_bottom": self.show_on_bottom_checkbox.isChecked(),
            "target_monitor": self.target_monitor_combobox.currentText(),
            "color": self.text_color_combobox.currentText(),
            "font_family": self.font_family_combobox.currentFont().family(),
            "marquee": self.marquee_checkbox.isChecked(),
            "marquee_speed": self.marquee_speed_combobox.currentText(),
            "outline": self.outline_checkbox.isChecked(),
            "outline_color": self.outline_color_combobox.currentText(),
        }

    def set_state(self, state: dict) -> None:
        opacity = coerce_int(state.get("opacity"))
        if opacity is not None:
            self.opacity_slider.setValue(opacity)
        font_size = coerce_int(state.get("font_size"))
        if font_size is not None:
            self.font_size_slider.setValue(font_size)
        if "text" in state:
            self.line_edit.setText(str(state.get("text") or ""))
        if "alignment" in state:
            index = self.text_position_combobox.findText(str(state["alignment"]))
            if index >= 0:
                self.text_position_combobox.setCurrentIndex(index)
        if "show_on_all_screen" in state:
            self.show_on_all_screen_checkbox.setChecked(bool(state["show_on_all_screen"]))
            self.show_all_screen = bool(state["show_on_all_screen"])
        if "show_on_bottom" in state:
            self.show_on_bottom_checkbox.setChecked(bool(state["show_on_bottom"]))
        if state.get("target_monitor") is not None:
            index = self.target_monitor_combobox.findText(str(state["target_monitor"]))
            if index >= 0:
                self.target_monitor_combobox.setCurrentIndex(index)
        if state.get("color") is not None:
            index = self.text_color_combobox.findText(str(state["color"]))
            if index >= 0:
                self.text_color_combobox.setCurrentIndex(index)
        if state.get("font_family"):
            self.font_family_combobox.setCurrentFont(QFont(str(state["font_family"])))
        if "marquee" in state:
            self.marquee_checkbox.setChecked(bool(state["marquee"]))
        if state.get("marquee_speed") is not None:
            index = self.marquee_speed_combobox.findText(str(state["marquee_speed"]))
            if index >= 0:
                self.marquee_speed_combobox.setCurrentIndex(index)
        if "outline" in state:
            self.outline_checkbox.setChecked(bool(state["outline"]))
        if state.get("outline_color") is not None:
            index = self.outline_color_combobox.findText(str(state["outline_color"]))
            if index >= 0:
                self.outline_color_combobox.setCurrentIndex(index)

    def start_draw_text_on_screen(self) -> None:
        front_engine_logger.info("[TextSettingUI] start_draw_text_on_screen")

        if not self.line_edit.text().strip():
            QMessageBox.warning(self, "Warning", language_wrapper.language_word_dict.get("not_prepare"))
            return

        def present_on_monitor(widget: TextWidget, monitor, _idx: int) -> None:
            widget.setScreen(monitor)
            widget.move(monitor.availableGeometry().topLeft())
            widget.showFullScreen()

        dispatch_to_monitors(
            parent=self,
            show_all_screen=self.show_all_screen,
            factory=lambda _monitor: self._create_text_widget(),
            present_primary=lambda widget: widget.showFullScreen(),
            present_on_monitor=present_on_monitor,
            preferred_monitor_index=resolve_preferred_monitor(self.target_monitor_combobox),
        )