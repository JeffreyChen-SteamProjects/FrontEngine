from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QSlider, QLabel, QLineEdit, QPushButton

from frontengine.show.text.draw_text import TextWidget


class TextSettingUI(QWidget):

    def __init__(self):
        super().__init__()
        self.grid_layout = QGridLayout()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        # Init variable
        self.text_widget_list = list()
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
        # Font size setting
        self.font_size_slider = QSlider()
        self.font_size_slider.setOrientation(Qt.Orientation.Horizontal)
        self.font_size_label = QLabel("Font size")
        self.font_size_slider.setMinimum(1)
        self.font_size_slider.setMaximum(300)
        self.font_size_slider.setValue(100)
        self.font_size_slider.setTickInterval(1)
        self.font_size_slider_value_label = QLabel(str(self.font_size_slider.value()))
        self.font_size_slider.actionTriggered.connect(self.font_size_trick)
        # Font input button
        self.line_edit = QLineEdit()
        # Start Button
        self.start_button = QPushButton("Start draw text on screen")
        self.start_button.clicked.connect(self.start_draw_text_on_screen)
        # Add to layout
        self.grid_layout.addWidget(self.opacity_label, 0, 0)
        self.grid_layout.addWidget(self.opacity_slider_value_label, 0, 1)
        self.grid_layout.addWidget(self.opacity_slider, 0, 2)
        self.grid_layout.addWidget(self.font_size_label, 1, 0)
        self.grid_layout.addWidget(self.font_size_slider_value_label, 1, 1)
        self.grid_layout.addWidget(self.font_size_slider, 1, 2)
        self.grid_layout.addWidget(self.start_button, 2, 0)
        self.grid_layout.addWidget(self.line_edit, 2, 2)
        self.setLayout(self.grid_layout)

    def opacity_trick(self):
        self.opacity_slider_value_label.setText(str(self.opacity_slider.value()))

    def font_size_trick(self):
        self.font_size_slider_value_label.setText(str(self.font_size_slider.value()))

    def start_draw_text_on_screen(self):
        text_widget = TextWidget(
            self.line_edit.text(),
            self.font_size_slider.value(),
            float(self.opacity_slider.value()) / 100
        )
        self.text_widget_list.append(text_widget)
        text_widget.showMaximized()

    def closeEvent(self, event) -> None:
        super().closeEvent(event)
        self.text_widget_list.clear()
