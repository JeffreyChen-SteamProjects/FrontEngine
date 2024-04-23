from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QWidget, QBoxLayout, QLineEdit, QPushButton, QSlider, QLabel, QHBoxLayout
from frontengine.utils.multi_language.language_wrapper import language_wrapper

from frontengine.ui.page.scene_setting.scene_tabs.tableview_model import add_row_data
from frontengine.utils.logging.loggin_instance import front_engine_logger


class TextSceneSettingUI(QWidget):

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.box_layout = QBoxLayout(QBoxLayout.Direction.TopToBottom)
        # Text button
        self.text_input = QLineEdit()
        self.text_input.setText(
            language_wrapper.language_word_dict.get("text")
        )
        self.text_button = QPushButton(
            language_wrapper.language_word_dict.get("scene_add_text")
        )
        self.text_button.clicked.connect(self.add_text)
        # Opacity slider
        self.opacity_slider = QSlider()
        self.opacity_slider.setMinimum(1)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setTickInterval(1)
        self.opacity_slider.setValue(20)
        self.opacity_slider.setOrientation(Qt.Orientation.Horizontal)
        self.opacity_label = QLabel()
        self.opacity_label.setText(language_wrapper.language_word_dict.get("Opacity"))
        self.opacity_box_h_layout = QHBoxLayout()
        self.opacity_box_h_layout.addWidget(self.opacity_label)
        self.opacity_box_h_layout.addWidget(self.opacity_slider)
        # Font size slider
        self.font_size_slider = QSlider()
        self.font_size_slider = QSlider()
        self.font_size_slider.setMinimum(1)
        self.font_size_slider.setMaximum(100)
        self.font_size_slider.setTickInterval(1)
        self.font_size_slider.setValue(100)
        self.font_size_slider.setOrientation(Qt.Orientation.Horizontal)
        self.front_size_label = QLabel()
        self.front_size_label.setText(language_wrapper.language_word_dict.get("Font size"))
        self.font_size_box_h_layout = QHBoxLayout()
        self.font_size_box_h_layout.addWidget(self.front_size_label)
        self.font_size_box_h_layout.addWidget(self.font_size_slider)
        # Position x input
        self.position_x_input_label = QLabel(language_wrapper.language_word_dict.get("position_x"))
        self.position_x_input = QLineEdit()
        self.position_x_input.setValidator(QIntValidator(0, 999999, self))
        self.position_x_layout = QHBoxLayout()
        self.position_x_layout.addWidget(self.position_x_input_label)
        self.position_x_layout.addWidget(self.position_x_input)
        # Position y input
        self.position_y_input_label = QLabel(language_wrapper.language_word_dict.get("position_y"))
        self.position_y_input = QLineEdit()
        self.position_y_input.setValidator(QIntValidator(0, 999999, self))
        self.position_y_layout = QHBoxLayout()
        self.position_y_layout.addWidget(self.position_y_input_label)
        self.position_y_layout.addWidget(self.position_y_input)
        # Set UI
        self.box_layout.addLayout(self.opacity_box_h_layout)
        self.box_layout.addLayout(self.font_size_box_h_layout)
        self.box_layout.addLayout(self.position_x_layout)
        self.box_layout.addLayout(self.position_y_layout)
        self.box_layout.addWidget(self.text_button)
        self.setLayout(self.box_layout)

    def add_text(self) -> None:
        row_data = ["TEXT", "", "", self.text_input.text(), str(self.opacity_slider.value()), "", "",
                    str(self.font_size_slider.value()), "", "", "",
                    self.position_x_input.text(), self.position_y_input.text()]
        front_engine_logger.info(f"add text, param: {row_data}")
        add_row_data(row_data)
