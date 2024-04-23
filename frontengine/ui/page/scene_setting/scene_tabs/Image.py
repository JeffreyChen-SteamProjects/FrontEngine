from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QWidget, QBoxLayout, QPushButton, QSlider, QLabel, QLineEdit, QHBoxLayout
from frontengine.utils.multi_language.language_wrapper import language_wrapper

from frontengine.ui.dialog.choose_file_dialog import choose_image
from frontengine.ui.page.scene_setting.scene_tabs.tableview_model import add_row_data
from frontengine.utils.logging.loggin_instance import front_engine_logger


class ImageSceneSettingUI(QWidget):

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.box_layout = QBoxLayout(QBoxLayout.Direction.TopToBottom)
        # Image button
        self.image_button = QPushButton(
            language_wrapper.language_word_dict.get("scene_add_image")
        )
        self.image_button.clicked.connect(self.add_image)
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
        self.box_layout.addLayout(self.position_x_layout)
        self.box_layout.addLayout(self.position_y_layout)
        self.box_layout.addWidget(self.image_button)
        self.setLayout(self.box_layout)

    def add_image(self) -> None:
        image_path = choose_image(self)
        if image_path is not None:
            row_data = ["IMAGE", image_path, "", "", str(self.opacity_slider.value()), "", "", "", "", "", "",
                        self.position_x_input.text(), self.position_y_input.text()]
            front_engine_logger.info(f"add image, param: {row_data}")
            add_row_data(row_data)
