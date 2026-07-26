"""
簡報頁：螢幕塗鴉、游標強調（亮環／漣漪／聚光燈）、按鍵顯示、區域放大鏡。
除了塗鴉需要接收滑鼠之外，其餘都是點擊穿透的覆蓋層。

The presentation page: screen annotation, cursor emphasis (ring, click ripple,
spotlight), a keystroke display and a region magnifier. Everything except the
annotation layer passes clicks straight through.
"""
from typing import List

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QGridLayout, QLabel, QPushButton, QSlider, QWidget,
)

from frontengine.show.presentation.annotation_overlay import (
    PEN_COLORS, TOOL_ERASER, TOOL_HIGHLIGHTER, TOOL_PEN, AnnotationOverlay,
)
from frontengine.show.presentation.cursor_effects import CursorEffectWidget
from frontengine.show.presentation.keystroke_display import KeystrokeDisplayWidget
from frontengine.show.presentation.magnifier import MagnifierWidget
from frontengine.ui.page.utils import build_target_monitor_combobox, coerce_int, resolve_preferred_monitor
from frontengine.utils.input_watch.input_watch_service import InputWatchService
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class PresentationSettingUI(QWidget):
    """簡報與教學工具設定頁。"""

    def __init__(self):
        front_engine_logger.info("[PresentationSettingUI] Init")
        super().__init__()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        self.annotation_widget_list: List[AnnotationOverlay] = []
        self.cursor_widget_list: List[CursorEffectWidget] = []
        self.keystroke_widget_list: List[KeystrokeDisplayWidget] = []
        self.magnifier_widget_list: List[MagnifierWidget] = []
        # 全域輸入監聽（按鍵顯示與點擊漣漪共用；pynput 不可用時自動停用）
        # Shared global input watching; disables itself without pynput.
        self.input_watch = InputWatchService(self)
        self.input_watch.key_pressed.connect(self._on_key_pressed, Qt.ConnectionType.QueuedConnection)
        self.input_watch.mouse_clicked.connect(self._on_mouse_clicked, Qt.ConnectionType.QueuedConnection)

        # Annotation
        self.annotate_label = QLabel(
            language_wrapper.language_word_dict.get("annotate_label", "Screen annotation"))
        self.annotate_tool_combobox = QComboBox()
        for tool, fallback in ((TOOL_PEN, "Pen"), (TOOL_HIGHLIGHTER, "Highlighter"),
                               (TOOL_ERASER, "Eraser")):
            self.annotate_tool_combobox.addItem(
                language_wrapper.language_word_dict.get(f"annotate_tool_{tool}", fallback), tool)
        self.annotate_tool_combobox.currentIndexChanged.connect(self._apply_annotation_settings)
        self.annotate_color_combobox = QComboBox()
        for name, hex_value in PEN_COLORS:
            self.annotate_color_combobox.addItem(name, hex_value)
        self.annotate_color_combobox.currentIndexChanged.connect(self._apply_annotation_settings)
        self.annotate_width_slider = QSlider(Qt.Orientation.Horizontal)
        self.annotate_width_slider.setRange(1, 40)
        self.annotate_width_slider.setValue(4)
        self.annotate_width_slider.valueChanged.connect(self._apply_annotation_settings)
        self.annotate_button = QPushButton(
            language_wrapper.language_word_dict.get("annotate_start", "Start drawing"))
        self.annotate_button.clicked.connect(self.toggle_annotation)
        self.annotate_undo_button = QPushButton(
            language_wrapper.language_word_dict.get("annotate_undo", "Undo"))
        self.annotate_undo_button.clicked.connect(self.undo_annotation)
        self.annotate_clear_button = QPushButton(
            language_wrapper.language_word_dict.get("annotate_clear", "Clear"))
        self.annotate_clear_button.clicked.connect(self.clear_annotation)

        # Cursor effects
        self.cursor_label = QLabel(
            language_wrapper.language_word_dict.get("cursor_effect_label", "Cursor emphasis"))
        self.cursor_ring_checkbox = QCheckBox(
            language_wrapper.language_word_dict.get("cursor_effect_ring", "Highlight"))
        self.cursor_ring_checkbox.setChecked(True)
        self.cursor_ripple_checkbox = QCheckBox(
            language_wrapper.language_word_dict.get("cursor_effect_ripple", "Click ripple"))
        self.cursor_ripple_checkbox.setChecked(True)
        self.cursor_spotlight_checkbox = QCheckBox(
            language_wrapper.language_word_dict.get("cursor_effect_spotlight", "Spotlight"))
        for checkbox in (self.cursor_ring_checkbox, self.cursor_ripple_checkbox,
                         self.cursor_spotlight_checkbox):
            checkbox.toggled.connect(self._apply_cursor_settings)
        self.cursor_button = QPushButton(
            language_wrapper.language_word_dict.get("cursor_effect_start", "Turn cursor effects on"))
        self.cursor_button.clicked.connect(self.toggle_cursor_effects)

        # Keystroke display
        self.keystroke_label = QLabel(
            language_wrapper.language_word_dict.get("keystroke_label", "Keystroke display"))
        self.keystroke_button = QPushButton(
            language_wrapper.language_word_dict.get("keystroke_start", "Show keystrokes"))
        self.keystroke_button.clicked.connect(self.toggle_keystrokes)

        # Magnifier
        self.magnifier_label = QLabel(
            language_wrapper.language_word_dict.get("magnifier_label", "Magnifier"))
        self.magnifier_zoom_combobox = QComboBox()
        self.magnifier_zoom_combobox.addItems(["1.5", "2.0", "3.0", "4.0", "6.0"])
        self.magnifier_zoom_combobox.setCurrentText("2.0")
        self.magnifier_zoom_combobox.currentIndexChanged.connect(self._apply_magnifier_settings)
        self.magnifier_button = QPushButton(
            language_wrapper.language_word_dict.get("magnifier_start", "Turn magnifier on"))
        self.magnifier_button.clicked.connect(self.toggle_magnifier)

        # Shared
        self.target_monitor_label = QLabel(
            language_wrapper.language_word_dict.get("target_monitor_label", "Target monitor"))
        self.target_monitor_combobox = build_target_monitor_combobox()
        self.hint_label = QLabel(
            language_wrapper.language_word_dict.get(
                "presentation_hint",
                "Drawing takes the mouse while it is on; the other overlays pass clicks through."))
        self.hint_label.setWordWrap(True)

        # Layout
        self.grid_layout.addWidget(self.annotate_label, 0, 0)
        self.grid_layout.addWidget(self.annotate_tool_combobox, 0, 1)
        self.grid_layout.addWidget(self.annotate_color_combobox, 0, 2)
        self.grid_layout.addWidget(self.annotate_width_slider, 1, 1, 1, 2)
        self.grid_layout.addWidget(self.annotate_button, 2, 0)
        self.grid_layout.addWidget(self.annotate_undo_button, 2, 1)
        self.grid_layout.addWidget(self.annotate_clear_button, 2, 2)
        self.grid_layout.addWidget(self.cursor_label, 3, 0)
        self.grid_layout.addWidget(self.cursor_ring_checkbox, 3, 1)
        self.grid_layout.addWidget(self.cursor_ripple_checkbox, 3, 2)
        self.grid_layout.addWidget(self.cursor_spotlight_checkbox, 4, 1)
        self.grid_layout.addWidget(self.cursor_button, 4, 0)
        self.grid_layout.addWidget(self.keystroke_label, 5, 0)
        self.grid_layout.addWidget(self.keystroke_button, 5, 1)
        self.grid_layout.addWidget(self.magnifier_label, 6, 0)
        self.grid_layout.addWidget(self.magnifier_zoom_combobox, 6, 1)
        self.grid_layout.addWidget(self.magnifier_button, 6, 2)
        self.grid_layout.addWidget(self.target_monitor_label, 7, 0)
        self.grid_layout.addWidget(self.target_monitor_combobox, 7, 1)
        self.grid_layout.addWidget(self.hint_label, 8, 0, 1, 3)

    # --- shared ----------------------------------------------------------
    def target_screen(self):
        """回傳要覆蓋的螢幕（未指定則主螢幕）。"""
        screens = QGuiApplication.screens()
        index = resolve_preferred_monitor(self.target_monitor_combobox)
        if index is not None and 0 <= index < len(screens):
            return screens[index]
        return QGuiApplication.primaryScreen()

    def _present(self, widget) -> None:
        screen = self.target_screen()
        if screen is not None:
            widget.setScreen(screen)
            widget.setGeometry(screen.geometry())
        widget.show()

    @staticmethod
    def _close_all(widgets: list) -> None:
        for widget in list(widgets):
            try:
                widget.close()
            except RuntimeError:
                pass
        widgets.clear()

    def _ensure_input_watch(self) -> None:
        """需要按鍵或點擊事件時才啟動全域監聽。"""
        if self.keystroke_widget_list or self.cursor_widget_list:
            self.input_watch.start()

    def _release_input_watch(self) -> None:
        if not self.keystroke_widget_list and not self.cursor_widget_list:
            self.input_watch.stop()

    # --- annotation ------------------------------------------------------
    def toggle_annotation(self) -> None:
        if self.annotation_widget_list:
            self.stop_annotation()
        else:
            self.start_annotation()

    def start_annotation(self) -> None:
        front_engine_logger.info("[PresentationSettingUI] start_annotation")
        self.stop_annotation()
        widget = AnnotationOverlay(
            self.annotate_color_combobox.currentData(), self.annotate_width_slider.value(),
            self.annotate_tool_combobox.currentData())
        widget.set_annotation_window_flag()
        self.annotation_widget_list.append(widget)
        self._present(widget)
        self.annotate_button.setText(
            language_wrapper.language_word_dict.get("annotate_stop", "Stop drawing"))

    def stop_annotation(self) -> None:
        self._close_all(self.annotation_widget_list)
        self.annotate_button.setText(
            language_wrapper.language_word_dict.get("annotate_start", "Start drawing"))

    def undo_annotation(self) -> None:
        for widget in self.annotation_widget_list:
            widget.undo()

    def clear_annotation(self) -> None:
        for widget in self.annotation_widget_list:
            widget.clear()

    def _apply_annotation_settings(self) -> None:
        for widget in self.annotation_widget_list[:]:
            try:
                widget.set_tool(self.annotate_tool_combobox.currentData())
                widget.set_pen(self.annotate_color_combobox.currentData(),
                               self.annotate_width_slider.value())
            except RuntimeError:
                self.annotation_widget_list.remove(widget)

    # --- cursor effects --------------------------------------------------
    def toggle_cursor_effects(self) -> None:
        if self.cursor_widget_list:
            self.stop_cursor_effects()
        else:
            self.start_cursor_effects()

    def start_cursor_effects(self) -> None:
        front_engine_logger.info("[PresentationSettingUI] start_cursor_effects")
        self.stop_cursor_effects()
        widget = CursorEffectWidget(
            ring=self.cursor_ring_checkbox.isChecked(),
            ripple=self.cursor_ripple_checkbox.isChecked(),
            spotlight=self.cursor_spotlight_checkbox.isChecked())
        widget.set_ui_window_flag(show_on_bottom=False)
        self.cursor_widget_list.append(widget)
        self._present(widget)
        widget.start_following()
        self._ensure_input_watch()
        self.cursor_button.setText(
            language_wrapper.language_word_dict.get("cursor_effect_stop", "Turn cursor effects off"))

    def stop_cursor_effects(self) -> None:
        self._close_all(self.cursor_widget_list)
        self._release_input_watch()
        self.cursor_button.setText(
            language_wrapper.language_word_dict.get("cursor_effect_start", "Turn cursor effects on"))

    def _apply_cursor_settings(self) -> None:
        for widget in self.cursor_widget_list[:]:
            try:
                widget.set_effects(
                    ring=self.cursor_ring_checkbox.isChecked(),
                    ripple=self.cursor_ripple_checkbox.isChecked(),
                    spotlight=self.cursor_spotlight_checkbox.isChecked())
            except RuntimeError:
                self.cursor_widget_list.remove(widget)

    # --- keystroke display -----------------------------------------------
    def toggle_keystrokes(self) -> None:
        if self.keystroke_widget_list:
            self.stop_keystrokes()
        else:
            self.start_keystrokes()

    def start_keystrokes(self) -> None:
        front_engine_logger.info("[PresentationSettingUI] start_keystrokes")
        self.stop_keystrokes()
        widget = KeystrokeDisplayWidget()
        widget.set_ui_window_flag(show_on_bottom=False)
        self.keystroke_widget_list.append(widget)
        self._present(widget)
        widget.start()
        self._ensure_input_watch()
        self.keystroke_button.setText(
            language_wrapper.language_word_dict.get("keystroke_stop", "Hide keystrokes"))

    def stop_keystrokes(self) -> None:
        self._close_all(self.keystroke_widget_list)
        self._release_input_watch()
        self.keystroke_button.setText(
            language_wrapper.language_word_dict.get("keystroke_start", "Show keystrokes"))

    def _on_key_pressed(self, keys) -> None:
        for widget in self.keystroke_widget_list[:]:
            try:
                widget.push_keys(keys)
            except RuntimeError:
                self.keystroke_widget_list.remove(widget)

    def _on_mouse_clicked(self, x: int, y: int) -> None:
        from PySide6.QtCore import QPoint

        for widget in self.cursor_widget_list[:]:
            try:
                widget.add_ripple(QPoint(int(x) - widget.x(), int(y) - widget.y()))
            except RuntimeError:
                self.cursor_widget_list.remove(widget)

    # --- magnifier -------------------------------------------------------
    def toggle_magnifier(self) -> None:
        if self.magnifier_widget_list:
            self.stop_magnifier()
        else:
            self.start_magnifier()

    def start_magnifier(self) -> None:
        front_engine_logger.info("[PresentationSettingUI] start_magnifier")
        self.stop_magnifier()
        widget = MagnifierWidget(float(self.magnifier_zoom_combobox.currentText()))
        widget.set_ui_window_flag(show_on_bottom=False)
        widget.resize(widget.view_size, widget.view_size)
        screen = self.target_screen()
        if screen is not None:
            widget.setScreen(screen)
            corner = screen.geometry().topRight()
            widget.move(corner.x() - widget.view_size - 20, corner.y() + 20)
        widget.show()
        self.magnifier_widget_list.append(widget)
        widget.start_following()
        self.magnifier_button.setText(
            language_wrapper.language_word_dict.get("magnifier_stop", "Turn magnifier off"))

    def stop_magnifier(self) -> None:
        self._close_all(self.magnifier_widget_list)
        self.magnifier_button.setText(
            language_wrapper.language_word_dict.get("magnifier_start", "Turn magnifier on"))

    def _apply_magnifier_settings(self) -> None:
        for widget in self.magnifier_widget_list[:]:
            try:
                widget.set_zoom(float(self.magnifier_zoom_combobox.currentText()))
            except RuntimeError:
                self.magnifier_widget_list.remove(widget)

    # --- preset state ----------------------------------------------------
    def get_state(self) -> dict:
        return {
            "annotate_tool": self.annotate_tool_combobox.currentData(),
            "annotate_color": self.annotate_color_combobox.currentText(),
            "annotate_width": self.annotate_width_slider.value(),
            "cursor_ring": self.cursor_ring_checkbox.isChecked(),
            "cursor_ripple": self.cursor_ripple_checkbox.isChecked(),
            "cursor_spotlight": self.cursor_spotlight_checkbox.isChecked(),
            "magnifier_zoom": self.magnifier_zoom_combobox.currentText(),
            "target_monitor": self.target_monitor_combobox.currentText(),
        }

    def set_state(self, state: dict) -> None:
        if state.get("annotate_tool") is not None:
            index = self.annotate_tool_combobox.findData(str(state["annotate_tool"]))
            if index >= 0:
                self.annotate_tool_combobox.setCurrentIndex(index)
        for combobox, key in ((self.annotate_color_combobox, "annotate_color"),
                              (self.magnifier_zoom_combobox, "magnifier_zoom"),
                              (self.target_monitor_combobox, "target_monitor")):
            if state.get(key) is not None:
                index = combobox.findText(str(state[key]))
                if index >= 0:
                    combobox.setCurrentIndex(index)
        width = coerce_int(state.get("annotate_width"))
        if width is not None:
            self.annotate_width_slider.setValue(width)
        for checkbox, key in ((self.cursor_ring_checkbox, "cursor_ring"),
                              (self.cursor_ripple_checkbox, "cursor_ripple"),
                              (self.cursor_spotlight_checkbox, "cursor_spotlight")):
            if key in state:
                checkbox.setChecked(bool(state[key]))
