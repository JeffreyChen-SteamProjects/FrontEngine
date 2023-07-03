from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QWidget, QBoxLayout, QMessageBox, QPushButton, QLineEdit, QLabel, QHBoxLayout

from frontengine.ui.setting.scene_setting.scene_tabs.tableview_model import add_row_data
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper

from frontengine import load_ui_file


class UISceneSettingUI(QWidget):

    def __init__(self):
        super().__init__()
        self.box_layout = QBoxLayout(QBoxLayout.Direction.TopToBottom)
        # UI button
        self.ui_button = QPushButton(
            language_wrapper.language_word_dict.get("scene_add_UI")
        )
        self.ui_path_input = QLineEdit()
        self.ui_path_input.setText(
            language_wrapper.language_word_dict.get("ui_path")
        )
        self.ui_button.clicked.connect(self.add_extend_ui_file)
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
        self.box_layout.addLayout(self.position_x_layout)
        self.box_layout.addLayout(self.position_y_layout)
        self.box_layout.addWidget(self.ui_path_input)
        self.box_layout.addWidget(self.ui_button)
        self.setLayout(self.box_layout)

    def add_extend_ui_file(self) -> None:
        if load_ui_file(self.ui_path_input.text()):
            add_row_data(
                ["EXTEND_UI_FILE", self.ui_path_input.text(), "", "", "", "", "",
                 "", "", "", "", self.position_x_input.text(), self.position_y_input.text()])
        else:
            ui_not_found_message = QMessageBox(self)
            ui_not_found_message.setText(
                language_wrapper.language_word_dict.get("cant_find_extend_ui_message_box_text"))
            ui_not_found_message.show()
            front_engine_logger.error(language_wrapper.language_word_dict.get("cant_find_extend_ui_message_box_text"))
