from PySide6.QtWidgets import QBoxLayout, QWidget, QLineEdit, QPushButton, QHBoxLayout
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class ChatInputDialog(QWidget):
    def __init__(self):
        super().__init__()
        self.box_layout = QBoxLayout(QBoxLayout.Direction.TopToBottom)
        self.chat_input = QLineEdit()
        self.send_text_button = QPushButton()
        self.send_text_button.setText(language_wrapper.language_word_dict.get("chat_scene_send_chat"))
        self.box_h_layout = QHBoxLayout()
        self.box_h_layout.addWidget(self.send_text_button)
        self.box_layout.addWidget(self.chat_input)
        self.box_layout.addLayout(self.box_h_layout)
        self.setWindowTitle(language_wrapper.language_word_dict.get("chat_scene_input_title"))
        self.setLayout(self.box_layout)
