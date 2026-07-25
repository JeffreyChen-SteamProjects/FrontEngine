"""
專注頁：把作用中視窗以外壓暗，以及蓋住會分心的螢幕區域（工作列、通知角落）。
兩者都是點擊穿透的覆蓋層，被蓋住的地方仍可正常操作。

The focus page: dim everything except the window you are working in, and cover
the parts of the screen that pull your eye away. Both pass clicks through, so
what is covered still works.
"""
from typing import List

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QComboBox, QGridLayout, QLabel, QPushButton, QSlider, QWidget

from frontengine.show.focus_shield.focus_shield_widget import (
    DimBackgroundWidget, DistractionMaskWidget,
)
from frontengine.ui.page.utils import build_target_monitor_combobox, coerce_int, resolve_preferred_monitor
from frontengine.utils.focus_shield.focus_shield import (
    REGION_BOTTOM, REGION_BOTTOM_RIGHT, REGION_FULL, REGION_LEFT, REGION_RIGHT, REGION_TOP,
)
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class FocusSettingUI(QWidget):
    """專注設定頁 / The focus settings page."""

    def __init__(self):
        front_engine_logger.info("[FocusSettingUI] Init")
        super().__init__()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        self.dim_widget_list: List[DimBackgroundWidget] = []
        self.mask_widget_list: List[DistractionMaskWidget] = []

        # Dim background windows
        self.dim_label = QLabel(
            language_wrapper.language_word_dict.get("focus_dim_label", "Dim background windows"))
        self.dim_slider = QSlider(Qt.Orientation.Horizontal)
        self.dim_slider.setRange(10, 90)
        self.dim_slider.setValue(45)
        self.dim_slider.valueChanged.connect(self._apply_dim_settings)
        self.dim_button = QPushButton(
            language_wrapper.language_word_dict.get("focus_dim_start", "Dim the background"))
        self.dim_button.clicked.connect(self.toggle_dim)

        # Mask a distraction
        self.mask_label = QLabel(
            language_wrapper.language_word_dict.get("focus_mask_label", "Cover a distraction"))
        self.mask_region_combobox = QComboBox()
        for region, fallback in (
            (REGION_BOTTOM, "Bottom strip (taskbar)"), (REGION_BOTTOM_RIGHT, "Bottom-right corner"),
            (REGION_TOP, "Top strip"), (REGION_LEFT, "Left edge"), (REGION_RIGHT, "Right edge"),
            (REGION_FULL, "Whole screen"),
        ):
            self.mask_region_combobox.addItem(
                language_wrapper.language_word_dict.get(f"focus_mask_region_{region}", fallback),
                region)
        self.mask_region_combobox.currentIndexChanged.connect(self._apply_mask_settings)
        self.mask_percent_slider = QSlider(Qt.Orientation.Horizontal)
        self.mask_percent_slider.setRange(1, 50)
        self.mask_percent_slider.setValue(6)
        self.mask_percent_slider.valueChanged.connect(self._apply_mask_settings)
        self.mask_button = QPushButton(
            language_wrapper.language_word_dict.get("focus_mask_start", "Cover it up"))
        self.mask_button.clicked.connect(self.toggle_mask)

        # Shared
        self.target_monitor_label = QLabel(
            language_wrapper.language_word_dict.get("target_monitor_label", "Target monitor"))
        self.target_monitor_combobox = build_target_monitor_combobox()
        self.hint_label = QLabel(
            language_wrapper.language_word_dict.get(
                "focus_hint",
                "Both overlays pass clicks through — what they cover still works, "
                "it just stops competing for your attention."))
        self.hint_label.setWordWrap(True)

        # Layout
        self.grid_layout.addWidget(self.dim_label, 0, 0)
        self.grid_layout.addWidget(self.dim_slider, 0, 1)
        self.grid_layout.addWidget(self.dim_button, 0, 2)
        self.grid_layout.addWidget(self.mask_label, 1, 0)
        self.grid_layout.addWidget(self.mask_region_combobox, 1, 1)
        self.grid_layout.addWidget(self.mask_button, 1, 2)
        self.grid_layout.addWidget(self.mask_percent_slider, 2, 1, 1, 2)
        self.grid_layout.addWidget(self.target_monitor_label, 3, 0)
        self.grid_layout.addWidget(self.target_monitor_combobox, 3, 1)
        self.grid_layout.addWidget(self.hint_label, 4, 0, 1, 3)

    # --- shared ----------------------------------------------------------
    def target_screen(self):
        screens = QGuiApplication.screens()
        index = resolve_preferred_monitor(self.target_monitor_combobox)
        if index is not None and 0 <= index < len(screens):
            return screens[index]
        return QGuiApplication.primaryScreen()

    @staticmethod
    def _close_all(widgets: list) -> None:
        for widget in list(widgets):
            try:
                widget.close()
            except RuntimeError:
                pass
        widgets.clear()

    # --- dim background --------------------------------------------------
    def toggle_dim(self) -> None:
        if self.dim_widget_list:
            self.stop_dim()
        else:
            self.start_dim()

    def start_dim(self) -> None:
        front_engine_logger.info("[FocusSettingUI] start_dim")
        self.stop_dim()
        screen = self.target_screen()
        if screen is None:
            return
        widget = DimBackgroundWidget(self.dim_slider.value())
        widget.set_ui_window_flag(show_on_bottom=False)
        widget.setScreen(screen)
        widget.setGeometry(screen.geometry())
        widget.show()
        widget.start_following()
        self.dim_widget_list.append(widget)
        self.dim_button.setText(
            language_wrapper.language_word_dict.get("focus_dim_stop", "Stop dimming"))

    def stop_dim(self) -> None:
        self._close_all(self.dim_widget_list)
        self.dim_button.setText(
            language_wrapper.language_word_dict.get("focus_dim_start", "Dim the background"))

    def _apply_dim_settings(self) -> None:
        for widget in list(self.dim_widget_list):
            try:
                widget.set_dim(self.dim_slider.value())
            except RuntimeError:
                self.dim_widget_list.remove(widget)

    # --- distraction mask ------------------------------------------------
    def toggle_mask(self) -> None:
        if self.mask_widget_list:
            self.stop_mask()
        else:
            self.start_mask()

    def start_mask(self) -> None:
        front_engine_logger.info("[FocusSettingUI] start_mask")
        self.stop_mask()
        screen = self.target_screen()
        if screen is None:
            return
        widget = DistractionMaskWidget(
            self.mask_region_combobox.currentData(), self.mask_percent_slider.value())
        widget.set_ui_window_flag(show_on_bottom=False)
        widget.setScreen(screen)
        geometry = screen.geometry()
        widget.setGeometry(widget.geometry_for(
            (geometry.x(), geometry.y(), geometry.width(), geometry.height())))
        widget.show()
        self.mask_widget_list.append(widget)
        self.mask_button.setText(
            language_wrapper.language_word_dict.get("focus_mask_stop", "Uncover"))

    def stop_mask(self) -> None:
        self._close_all(self.mask_widget_list)
        self.mask_button.setText(
            language_wrapper.language_word_dict.get("focus_mask_start", "Cover it up"))

    def _apply_mask_settings(self) -> None:
        """區域或比例改變時，直接把已開啟的遮罩移到新位置。"""
        screen = self.target_screen()
        if screen is None:
            return
        geometry = screen.geometry()
        bounds = (geometry.x(), geometry.y(), geometry.width(), geometry.height())
        for widget in list(self.mask_widget_list):
            try:
                widget.set_region(self.mask_region_combobox.currentData(),
                                  self.mask_percent_slider.value())
                widget.setGeometry(widget.geometry_for(bounds))
            except RuntimeError:
                self.mask_widget_list.remove(widget)

    # --- preset state ----------------------------------------------------
    def get_state(self) -> dict:
        return {
            "dim": self.dim_slider.value(),
            "mask_region": self.mask_region_combobox.currentData(),
            "mask_percent": self.mask_percent_slider.value(),
            "target_monitor": self.target_monitor_combobox.currentText(),
        }

    def set_state(self, state: dict) -> None:
        for slider, key in ((self.dim_slider, "dim"), (self.mask_percent_slider, "mask_percent")):
            value = coerce_int(state.get(key))
            if value is not None:
                slider.setValue(value)
        if state.get("mask_region") is not None:
            index = self.mask_region_combobox.findData(str(state["mask_region"]))
            if index >= 0:
                self.mask_region_combobox.setCurrentIndex(index)
        if state.get("target_monitor") is not None:
            index = self.target_monitor_combobox.findText(str(state["target_monitor"]))
            if index >= 0:
                self.target_monitor_combobox.setCurrentIndex(index)
