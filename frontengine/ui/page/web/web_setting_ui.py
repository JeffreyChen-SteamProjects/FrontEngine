from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QSlider, QLineEdit, QPushButton, QCheckBox

from frontengine.show.web.webview import WebWidget
from frontengine.ui.page.utils import dispatch_to_monitors
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class WEBSettingUI(QWidget):
    def __init__(self):
        front_engine_logger.info("[WEBSettingUI] Init")
        super().__init__()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        # Init variable
        self.web_widget_list = []
        self.show_all_screen = False
        self.open_file = False
        self.enable_input = False

        # Opacity setting
        self.opacity_label = QLabel(language_wrapper.language_word_dict.get("Opacity"))
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(1, 100)
        self.opacity_slider.setValue(20)
        self.opacity_slider_value_label = QLabel(str(self.opacity_slider.value()))
        self.opacity_slider.valueChanged.connect(self.opacity_trick)

        # WEB URL input
        self.web_url_input = QLineEdit()

        # Start url button
        self.start_button = QPushButton(language_wrapper.language_word_dict.get("web_setting_open_url"))
        self.start_button.clicked.connect(self.start_open_web_with_url)

        # Show on all screen
        self.show_on_all_screen_checkbox = QCheckBox(language_wrapper.language_word_dict.get("Show on all screen"))
        self.show_on_all_screen_checkbox.clicked.connect(self.set_show_all_screen)

        # Open local html file
        self.open_local_html_checkbox = QCheckBox(
            language_wrapper.language_word_dict.get("web_setting_open_local_file"))
        self.open_local_html_checkbox.clicked.connect(self.set_open_file)

        # Enable input
        self.enable_input_checkbox = QCheckBox(language_wrapper.language_word_dict.get("web_setting_open_enable_input"))
        self.enable_input_checkbox.clicked.connect(self.set_enable_input)

        # Show on bottom
        self.show_on_bottom_checkbox = QCheckBox(language_wrapper.language_word_dict.get("Show on bottom"))

        # Layout
        self.grid_layout.addWidget(self.opacity_label, 0, 0)
        self.grid_layout.addWidget(self.opacity_slider_value_label, 0, 1)
        self.grid_layout.addWidget(self.opacity_slider, 0, 2)
        self.grid_layout.addWidget(self.open_local_html_checkbox, 1, 0)
        self.grid_layout.addWidget(self.enable_input_checkbox, 1, 1)
        self.grid_layout.addWidget(self.show_on_all_screen_checkbox, 2, 0)
        self.grid_layout.addWidget(self.show_on_bottom_checkbox, 2, 1)
        self.grid_layout.addWidget(self.start_button, 3, 0)
        self.grid_layout.addWidget(self.web_url_input, 3, 2)

    def set_show_all_screen(self) -> None:
        front_engine_logger.info("[WEBSettingUI] set_show_all_screen")
        self.show_all_screen = self.show_on_all_screen_checkbox.isChecked()

    def set_open_file(self) -> None:
        front_engine_logger.info("[WEBSettingUI] set_open_file")
        self.open_file = self.open_local_html_checkbox.isChecked()

    def set_enable_input(self) -> None:
        front_engine_logger.info("[WEBSettingUI] set_enable_input")
        self.enable_input = self.enable_input_checkbox.isChecked()

    def _create_web_widget(self) -> WebWidget:
        front_engine_logger.info("[WEBSettingUI] _create_web_widget")
        web_widget = WebWidget(self.web_url_input.text(), is_file=self.open_file)
        web_widget.set_ui_variable(float(self.opacity_slider.value()) / 100)
        web_widget.set_ui_window_flag(
            enable_input=self.enable_input,
            show_on_bottom=self.show_on_bottom_checkbox.isChecked()
        )
        self.web_widget_list.append(web_widget)
        return web_widget

    def opacity_trick(self) -> None:
        front_engine_logger.info("[WEBSettingUI] opacity_trick")
        self.opacity_slider_value_label.setText(str(self.opacity_slider.value()))

    def get_state(self) -> dict:
        return {
            "opacity": self.opacity_slider.value(),
            "url": self.web_url_input.text(),
            "open_file": self.open_local_html_checkbox.isChecked(),
            "enable_input": self.enable_input_checkbox.isChecked(),
            "show_on_all_screen": self.show_on_all_screen_checkbox.isChecked(),
            "show_on_bottom": self.show_on_bottom_checkbox.isChecked(),
        }

    def set_state(self, state: dict) -> None:
        if "opacity" in state:
            self.opacity_slider.setValue(int(state["opacity"]))
        if "url" in state:
            self.web_url_input.setText(str(state.get("url") or ""))
        if "open_file" in state:
            self.open_local_html_checkbox.setChecked(bool(state["open_file"]))
            self.open_file = bool(state["open_file"])
        if "enable_input" in state:
            self.enable_input_checkbox.setChecked(bool(state["enable_input"]))
            self.enable_input = bool(state["enable_input"])
        if "show_on_all_screen" in state:
            self.show_on_all_screen_checkbox.setChecked(bool(state["show_on_all_screen"]))
            self.show_all_screen = bool(state["show_on_all_screen"])
        if "show_on_bottom" in state:
            self.show_on_bottom_checkbox.setChecked(bool(state["show_on_bottom"]))

    def start_open_web_with_url(self) -> None:
        front_engine_logger.info("[WEBSettingUI] start_open_web_with_url")

        def present_on_monitor(widget: WebWidget, monitor, _idx: int) -> None:
            widget.setScreen(monitor)
            widget.move(monitor.availableGeometry().topLeft())
            widget.showFullScreen()

        dispatch_to_monitors(
            parent=self,
            show_all_screen=self.show_all_screen,
            factory=lambda _monitor: self._create_web_widget(),
            present_primary=lambda widget: widget.showFullScreen(),
            present_on_monitor=present_on_monitor,
        )