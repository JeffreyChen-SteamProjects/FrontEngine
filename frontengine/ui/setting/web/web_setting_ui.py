from PySide6.QtCore import Qt
from PySide6.QtGui import QScreen
from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QSlider, QLineEdit, QPushButton, QRadioButton

from frontengine.show.web.webview import WebWidget


class WEBSettingUI(QWidget):

    def __init__(self):
        super().__init__()
        self.grid_layout = QGridLayout()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        # Init variable
        self.web_widget_list = list()
        self.show_all_screen = False
        # Opacity setting
        self.opacity_slider = QSlider()
        self.opacity_slider.setOrientation(Qt.Orientation.Horizontal)
        self.opacity_label = QLabel("Opacity")
        self.opacity_slider.setMinimum(1)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(20)
        self.opacity_slider.setTickInterval(1)
        self.opacity_slider_value_label = QLabel(str(self.opacity_slider.value()))
        self.opacity_slider.actionTriggered.connect(self.opacity_trick)
        # WEB URL input
        self.web_url_input = QLineEdit()
        # Start button
        self.start_button = QPushButton("Open web with url")
        self.start_button.clicked.connect(self.start_open_web)
        # Show on all screen
        self.show_on_all_screen_button = QRadioButton("Show on all screen")
        self.show_on_all_screen_button.clicked.connect(self.set_show_all_screen)
        # Add to layout
        self.grid_layout.addWidget(self.opacity_label, 0, 0)
        self.grid_layout.addWidget(self.opacity_slider_value_label, 0, 1)
        self.grid_layout.addWidget(self.opacity_slider, 0, 2)
        self.grid_layout.addWidget(self.start_button, 1, 0)
        self.grid_layout.addWidget(self.show_on_all_screen_button, 1, 1)
        self.grid_layout.addWidget(self.web_url_input, 1, 2)
        self.setLayout(self.grid_layout)

    def set_show_all_screen(self):
        self.show_all_screen = self.show_on_all_screen_button.isChecked()

    def _create_web_widget(self):
        web_widget = WebWidget(
            self.web_url_input.text(),
            float(self.opacity_slider.value()) / 100
        )
        self.web_widget_list.append(web_widget)
        return web_widget

    def opacity_trick(self):
        self.opacity_slider_value_label.setText(str(self.opacity_slider.value()))

    def start_open_web(self):
        if self.show_all_screen:
            web_widget = self._create_web_widget()
            web_widget.showMaximized()
        else:
            monitors = QScreen.virtualSiblings(self.screen())
            for screen in monitors:
                monitor = screen.availableGeometry()
                web_widget = self._create_web_widget()
                web_widget.move(monitor.left(), monitor.top())
                web_widget.showMaximized()
