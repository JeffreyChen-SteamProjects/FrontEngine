from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QWidget, QBoxLayout, QPushButton, QSlider, QLabel, QLineEdit, QHBoxLayout
from frontengine.utils.multi_language.language_wrapper import language_wrapper

from frontengine.ui.dialog.choose_file_dialog import choose_gif
from frontengine.ui.page.scene_setting.scene_tabs.tableview_model import add_row_data
from frontengine.utils.logging.loggin_instance import front_engine_logger


class GIFSceneSettingUI(QWidget):

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.box_layout = QBoxLayout(QBoxLayout.Direction.TopToBottom)
        # GIF button
        self.gif_button = QPushButton(
            language_wrapper.language_word_dict.get("scene_add_gif")
        )
        self.gif_button.clicked.connect(self.add_gif)
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
        # Speed slider
        self.speed_slider = QSlider()
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(100)
        self.speed_slider.setTickInterval(1)
        self.speed_slider.setValue(100)
        self.speed_slider.setOrientation(Qt.Orientation.Horizontal)
        self.speed_label = QLabel()
        self.speed_label.setText(language_wrapper.language_word_dict.get("Speed"))
        self.speed_box_h_layout = QHBoxLayout()
        self.speed_box_h_layout.addWidget(self.speed_label)
        self.speed_box_h_layout.addWidget(self.speed_slider)
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
        self.box_layout.addLayout(self.speed_box_h_layout)
        self.box_layout.addLayout(self.position_x_layout)
        self.box_layout.addLayout(self.position_y_layout)
        self.box_layout.addWidget(self.gif_button)
        self.setLayout(self.box_layout)

    def add_gif(self) -> None:
        gif_path = choose_gif(self)
        if gif_path is not None:
            row_data = ["GIF", gif_path, "", "", str(self.opacity_slider.value()), str(self.speed_slider.value()),
                        "", "", "", "", "", self.position_x_input.text(), self.position_y_input.text()]
            front_engine_logger.info(f"add gif, param: {row_data}")
            add_row_data(row_data)
