"""
護眼頁：色彩濾鏡、閱讀尺、休息提醒。三者都是點擊穿透的覆蓋層，
開著也不影響底下的操作。

The eye-comfort page: colour filter, reading ruler and break reminders. All
three are click-through overlays, so they never get in the way of your work.
"""
from typing import List

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QGridLayout, QLabel, QPushButton, QSlider, QWidget,
)

from frontengine.show.screen_care.color_vision_widget import ColorVisionWidget
from frontengine.show.screen_care.screen_filter import (
    FILTER_COLORS, ReadingRulerWidget, ScreenFilterWidget,
)
from frontengine.ui.page.utils import build_target_monitor_combobox, coerce_int, resolve_preferred_monitor
from frontengine.utils.break_reminder.break_reminder import (
    PHASE_REST, PHASE_WORK, BreakReminder,
)
from frontengine.utils.color_vision.color_vision import (
    KIND_ACHROMATOPSIA, KIND_DEUTERANOPIA, KIND_PROTANOPIA, KIND_TRITANOPIA,
)
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class ScreenCareSettingUI(QWidget):
    """護眼設定頁 / The eye-comfort settings page."""

    BREAK_TICK_MS = 1000

    def __init__(self):
        front_engine_logger.info("[ScreenCareSettingUI] Init")
        super().__init__()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        # 目前開著的覆蓋層 / Overlays currently on screen
        self.filter_widget_list: List[ScreenFilterWidget] = []
        self.ruler_widget_list: List[ReadingRulerWidget] = []
        self.break_overlay_list: List[ScreenFilterWidget] = []
        self.color_vision_widget_list: List[ColorVisionWidget] = []

        # Colour filter
        self.filter_label = QLabel(
            language_wrapper.language_word_dict.get("screen_filter_label", "Screen filter"))
        self.filter_color_combobox = QComboBox()
        for name, hex_value in FILTER_COLORS:
            self.filter_color_combobox.addItem(
                language_wrapper.language_word_dict.get(f"screen_filter_color_{name.lower()}", name),
                hex_value)
        self.filter_strength_label = QLabel(
            language_wrapper.language_word_dict.get("screen_filter_strength", "Strength"))
        self.filter_strength_slider = QSlider(Qt.Orientation.Horizontal)
        self.filter_strength_slider.setRange(1, 80)
        self.filter_strength_slider.setValue(15)
        self.filter_strength_slider.valueChanged.connect(self._apply_filter_settings)
        self.filter_color_combobox.currentIndexChanged.connect(self._apply_filter_settings)
        self.filter_button = QPushButton(
            language_wrapper.language_word_dict.get("screen_filter_start", "Turn filter on"))
        self.filter_button.clicked.connect(self.toggle_filter)

        # Reading ruler
        self.ruler_label = QLabel(
            language_wrapper.language_word_dict.get("reading_ruler_label", "Reading ruler"))
        self.ruler_band_combobox = QComboBox()
        self.ruler_band_combobox.addItems(["60", "90", "120", "160", "220"])
        self.ruler_band_combobox.setCurrentText("90")
        self.ruler_band_combobox.currentIndexChanged.connect(self._apply_ruler_settings)
        self.ruler_strength_slider = QSlider(Qt.Orientation.Horizontal)
        self.ruler_strength_slider.setRange(10, 80)
        self.ruler_strength_slider.setValue(45)
        self.ruler_strength_slider.valueChanged.connect(self._apply_ruler_settings)
        self.ruler_button = QPushButton(
            language_wrapper.language_word_dict.get("reading_ruler_start", "Turn ruler on"))
        self.ruler_button.clicked.connect(self.toggle_ruler)

        # Break reminder (20-20-20)
        self.break_reminder = BreakReminder()
        self.break_timer = QTimer(self)
        self.break_timer.timeout.connect(self._tick_break_reminder)
        self.break_label = QLabel(
            language_wrapper.language_word_dict.get("break_reminder_label", "Eye breaks (min / sec)"))
        self.break_minutes_combobox = QComboBox()
        self.break_minutes_combobox.addItems(["10", "20", "30", "45", "60"])
        self.break_minutes_combobox.setCurrentText("20")
        self.break_seconds_combobox = QComboBox()
        self.break_seconds_combobox.addItems(["20", "30", "60", "120"])
        self.break_seconds_combobox.setCurrentText("20")
        self.break_button = QPushButton(
            language_wrapper.language_word_dict.get("break_reminder_start", "Start eye breaks"))
        self.break_button.clicked.connect(self.toggle_break_reminder)

        # Shared
        self.all_screens_checkbox = QCheckBox(
            language_wrapper.language_word_dict.get("Show on all screen", "Show on all screen"))
        # 色覺模擬：把整個畫面換成某種色盲看到的樣子（不透明覆蓋層）
        # Colour-vision simulation: repaint the screen as a given deficiency
        # sees it, using an opaque overlay.
        self.color_vision_label = QLabel(
            language_wrapper.language_word_dict.get("color_vision_label", "Colour vision"))
        self.color_vision_combobox = QComboBox()
        for kind, key, fallback in (
                (KIND_PROTANOPIA, "color_vision_protanopia", "Protanopia (red)"),
                (KIND_DEUTERANOPIA, "color_vision_deuteranopia", "Deuteranopia (green)"),
                (KIND_TRITANOPIA, "color_vision_tritanopia", "Tritanopia (blue)"),
                (KIND_ACHROMATOPSIA, "color_vision_achromatopsia", "Achromatopsia (none)")):
            self.color_vision_combobox.addItem(
                language_wrapper.language_word_dict.get(key, fallback), kind)
        self.color_vision_combobox.currentIndexChanged.connect(self._apply_color_vision_settings)
        self.color_vision_slider = QSlider(Qt.Orientation.Horizontal)
        self.color_vision_slider.setRange(0, 100)
        self.color_vision_slider.setValue(100)
        self.color_vision_slider.valueChanged.connect(self._apply_color_vision_settings)
        self.color_vision_button = QPushButton(
            language_wrapper.language_word_dict.get("color_vision_start", "Simulate"))
        self.color_vision_button.clicked.connect(self.toggle_color_vision)

        self.target_monitor_label = QLabel(
            language_wrapper.language_word_dict.get("target_monitor_label", "Target monitor"))
        self.target_monitor_combobox = build_target_monitor_combobox()
        self.hint_label = QLabel(
            language_wrapper.language_word_dict.get(
                "screen_care_hint",
                "These overlays pass clicks through, so everything underneath keeps working."))
        self.hint_label.setWordWrap(True)

        # Layout
        self.grid_layout.addWidget(self.filter_label, 0, 0)
        self.grid_layout.addWidget(self.filter_color_combobox, 0, 1)
        self.grid_layout.addWidget(self.filter_button, 0, 2)
        self.grid_layout.addWidget(self.filter_strength_label, 1, 0)
        self.grid_layout.addWidget(self.filter_strength_slider, 1, 1, 1, 2)
        self.grid_layout.addWidget(self.ruler_label, 2, 0)
        self.grid_layout.addWidget(self.ruler_band_combobox, 2, 1)
        self.grid_layout.addWidget(self.ruler_button, 2, 2)
        self.grid_layout.addWidget(self.ruler_strength_slider, 3, 1, 1, 2)
        self.grid_layout.addWidget(self.break_label, 4, 0)
        self.grid_layout.addWidget(self.break_minutes_combobox, 4, 1)
        self.grid_layout.addWidget(self.break_seconds_combobox, 4, 2)
        self.grid_layout.addWidget(self.break_button, 5, 0)
        self.grid_layout.addWidget(self.color_vision_label, 6, 0)
        self.grid_layout.addWidget(self.color_vision_combobox, 6, 1)
        self.grid_layout.addWidget(self.color_vision_button, 6, 2)
        self.grid_layout.addWidget(self.color_vision_slider, 7, 1, 1, 2)
        self.grid_layout.addWidget(self.all_screens_checkbox, 8, 0)
        self.grid_layout.addWidget(self.target_monitor_label, 9, 0)
        self.grid_layout.addWidget(self.target_monitor_combobox, 9, 1)
        self.grid_layout.addWidget(self.hint_label, 10, 0, 1, 3)

    # --- shared helpers --------------------------------------------------
    def target_screens(self) -> list:
        """依設定回傳要覆蓋的螢幕清單。"""
        screens = QGuiApplication.screens()
        if self.all_screens_checkbox.isChecked():
            return list(screens)
        index = resolve_preferred_monitor(self.target_monitor_combobox)
        if index is not None and 0 <= index < len(screens):
            return [screens[index]]
        primary = QGuiApplication.primaryScreen()
        return [primary] if primary is not None else []

    @staticmethod
    def _present(widget, screen) -> None:
        """把覆蓋層鋪滿指定螢幕。"""
        geometry = screen.geometry()
        widget.setScreen(screen)
        widget.setGeometry(geometry)
        widget.show()

    @staticmethod
    def _close_all(widgets: list) -> None:
        for widget in list(widgets):
            try:
                widget.close()
            except RuntimeError:
                pass  # already destroyed
        widgets.clear()

    # --- colour filter ---------------------------------------------------
    def toggle_filter(self) -> None:
        """開關色彩濾鏡。"""
        if self.filter_widget_list:
            self.stop_filter()
        else:
            self.start_filter()

    def start_filter(self) -> None:
        front_engine_logger.info("[ScreenCareSettingUI] start_filter")
        self.stop_filter()
        for screen in self.target_screens():
            widget = ScreenFilterWidget(
                self.filter_color_combobox.currentData(), self.filter_strength_slider.value())
            widget.set_ui_window_flag(show_on_bottom=False)
            self.filter_widget_list.append(widget)
            self._present(widget, screen)
        self.filter_button.setText(
            language_wrapper.language_word_dict.get("screen_filter_stop", "Turn filter off"))

    def stop_filter(self) -> None:
        self._close_all(self.filter_widget_list)
        self.filter_button.setText(
            language_wrapper.language_word_dict.get("screen_filter_start", "Turn filter on"))

    def _apply_filter_settings(self) -> None:
        """滑桿或顏色改變時即時套用到已開啟的濾鏡。"""
        for widget in self.filter_widget_list[:]:
            try:
                widget.set_filter(
                    self.filter_color_combobox.currentData(), self.filter_strength_slider.value())
            except RuntimeError:
                self.filter_widget_list.remove(widget)

    # --- reading ruler ---------------------------------------------------
    def toggle_ruler(self) -> None:
        """開關閱讀尺。"""
        if self.ruler_widget_list:
            self.stop_ruler()
        else:
            self.start_ruler()

    def start_ruler(self) -> None:
        front_engine_logger.info("[ScreenCareSettingUI] start_ruler")
        self.stop_ruler()
        for screen in self.target_screens():
            widget = ReadingRulerWidget(
                int(self.ruler_band_combobox.currentText()), self.ruler_strength_slider.value())
            widget.set_ui_window_flag(show_on_bottom=False)
            self.ruler_widget_list.append(widget)
            self._present(widget, screen)
            widget.start_following()
        self.ruler_button.setText(
            language_wrapper.language_word_dict.get("reading_ruler_stop", "Turn ruler off"))

    def stop_ruler(self) -> None:
        self._close_all(self.ruler_widget_list)
        self.ruler_button.setText(
            language_wrapper.language_word_dict.get("reading_ruler_start", "Turn ruler on"))

    def _apply_ruler_settings(self) -> None:
        for widget in self.ruler_widget_list[:]:
            try:
                widget.set_band(
                    int(self.ruler_band_combobox.currentText()), self.ruler_strength_slider.value())
            except RuntimeError:
                self.ruler_widget_list.remove(widget)

    # --- break reminder --------------------------------------------------
    def toggle_break_reminder(self) -> None:
        """開關護眼休息提醒。"""
        if self.break_reminder.running:
            self.stop_break_reminder()
        else:
            self.start_break_reminder()

    def start_break_reminder(self) -> None:
        self.break_reminder.work_minutes = int(self.break_minutes_combobox.currentText())
        self.break_reminder.rest_seconds = int(self.break_seconds_combobox.currentText())
        self.break_reminder.start()
        front_engine_logger.info(
            f"[ScreenCareSettingUI] break reminder started | work={self.break_reminder.work_minutes}min")
        self.break_timer.start(self.BREAK_TICK_MS)
        self.break_button.setText(
            language_wrapper.language_word_dict.get("break_reminder_stop", "Stop eye breaks"))

    def stop_break_reminder(self) -> None:
        self.break_reminder.stop()
        self.break_timer.stop()
        self._close_all(self.break_overlay_list)
        self.break_button.setText(
            language_wrapper.language_word_dict.get("break_reminder_start", "Start eye breaks"))

    def _tick_break_reminder(self) -> None:
        """時間到就顯示或收起休息畫面。"""
        phase = self.break_reminder.tick()
        if phase == PHASE_REST:
            self.show_break_overlay()
        elif phase == PHASE_WORK:
            self._close_all(self.break_overlay_list)

    def show_break_overlay(self) -> None:
        """休息時把畫面壓暗一層當提示（仍可點擊穿透，不會擋住緊急操作）。"""
        front_engine_logger.info("[ScreenCareSettingUI] break time")
        self._close_all(self.break_overlay_list)
        for screen in self.target_screens():
            overlay = ScreenFilterWidget("#000000", 55)
            overlay.set_ui_window_flag(show_on_bottom=False)
            self.break_overlay_list.append(overlay)
            self._present(overlay, screen)

    # --- preset state ----------------------------------------------------
    # --- colour vision ---------------------------------------------------
    def toggle_color_vision(self) -> None:
        if self.color_vision_widget_list:
            self.stop_color_vision()
        else:
            self.start_color_vision()

    def start_color_vision(self) -> None:
        """在每個目標螢幕開一層色覺模擬。"""
        front_engine_logger.info("[ScreenCareSettingUI] start_color_vision")
        self.stop_color_vision()
        for screen in self.target_screens():
            widget = ColorVisionWidget(self.color_vision_combobox.currentData(),
                                       self.color_vision_slider.value() / 100.0)
            widget.set_ui_window_flag(show_on_bottom=False)
            self._present(widget, screen)
            widget.start()
            self.color_vision_widget_list.append(widget)
        self.color_vision_button.setText(
            language_wrapper.language_word_dict.get("color_vision_stop", "Stop simulating"))

    def stop_color_vision(self) -> None:
        self._close_all(self.color_vision_widget_list)
        self.color_vision_button.setText(
            language_wrapper.language_word_dict.get("color_vision_start", "Simulate"))

    def _apply_color_vision_settings(self) -> None:
        for widget in self.color_vision_widget_list[:]:
            try:
                widget.set_simulation(self.color_vision_combobox.currentData(),
                                      self.color_vision_slider.value() / 100.0)
            except RuntimeError:
                self.color_vision_widget_list.remove(widget)

    def get_state(self) -> dict:
        return {
            "color_vision_kind": self.color_vision_combobox.currentData(),
            "color_vision_severity": self.color_vision_slider.value(),
            "filter_color": self.filter_color_combobox.currentText(),
            "filter_strength": self.filter_strength_slider.value(),
            "ruler_band": self.ruler_band_combobox.currentText(),
            "ruler_strength": self.ruler_strength_slider.value(),
            "break_minutes": self.break_minutes_combobox.currentText(),
            "break_seconds": self.break_seconds_combobox.currentText(),
            "all_screens": self.all_screens_checkbox.isChecked(),
            "target_monitor": self.target_monitor_combobox.currentText(),
        }

    def set_state(self, state: dict) -> None:
        for combobox, key in (
            (self.filter_color_combobox, "filter_color"),
            (self.ruler_band_combobox, "ruler_band"),
            (self.break_minutes_combobox, "break_minutes"),
            (self.break_seconds_combobox, "break_seconds"),
            (self.target_monitor_combobox, "target_monitor"),
        ):
            if state.get(key) is not None:
                index = combobox.findText(str(state[key]))
                if index >= 0:
                    combobox.setCurrentIndex(index)
        kind = state.get("color_vision_kind")
        if kind is not None:
            index = self.color_vision_combobox.findData(str(kind))
            if index >= 0:
                self.color_vision_combobox.setCurrentIndex(index)
        for slider, key in ((self.filter_strength_slider, "filter_strength"),
                            (self.ruler_strength_slider, "ruler_strength"),
                            (self.color_vision_slider, "color_vision_severity")):
            value = coerce_int(state.get(key))
            if value is not None:
                slider.setValue(value)
        if "all_screens" in state:
            self.all_screens_checkbox.setChecked(bool(state["all_screens"]))
