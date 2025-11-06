from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QSlider, QLineEdit, QPushButton, QCheckBox, QDialog

from frontengine.show.web.webview import WebWidget
from frontengine.ui.page.utils import create_monitor_selection_dialog
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

    def start_open_web_with_url(self) -> None:
        front_engine_logger.info("[WEBSettingUI] start_open_web_with_url")
        monitors = QGuiApplication.screens()
        if not self.show_all_screen and len(monitors) <= 1:
            web_widget = self._create_web_widget()
            web_widget.showFullScreen()
        elif not self.show_all_screen and len(monitors) >= 2:
            input_dialog, combobox = create_monitor_selection_dialog(self, monitors)
            result = input_dialog.exec()
            if result == QDialog.DialogCode.Accepted:
                select_monitor_index = int(combobox.currentText())
                if len(monitors) > select_monitor_index:
                    monitor = monitors[select_monitor_index]
                    web_widget = self._create_web_widget()
                    web_widget.setScreen(monitor)
                    web_widget.move(monitor.availableGeometry().topLeft())
                    web_widget.showFullScreen()
        else:
            for monitor in monitors:
                web_widget = self._create_web_widget()
                web_widget.setScreen(monitor)
                web_widget.move(monitor.availableGeometry().topLeft())
                web_widget.showFullScreen()