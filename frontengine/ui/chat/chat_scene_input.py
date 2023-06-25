from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QBoxLayout, QWidget, QPushButton, QHBoxLayout, QTextEdit

from frontengine.show.chat.chat_toast import ChatToast
from frontengine.ui.chat.chatthread import MESSAGE_QUEUE
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class ChatInputDialog(QWidget):
    def __init__(self):
        super().__init__()
        self.box_layout = QBoxLayout(QBoxLayout.Direction.TopToBottom)
        self.chat_input = QTextEdit()
        self.send_text_button = QPushButton()
        self.send_text_button.setText(language_wrapper.language_word_dict.get("chat_scene_send_chat"))
        self.box_h_layout = QHBoxLayout()
        self.box_h_layout.addWidget(self.send_text_button)
        self.box_layout.addWidget(self.chat_input)
        self.box_layout.addLayout(self.box_h_layout)
        self.setWindowTitle(language_wrapper.language_word_dict.get("chat_scene_input_title"))
        self.setLayout(self.box_layout)
        # Get message timer
        self.get_message_timer = QTimer()
        self.get_message_timer.setInterval(5000)
        self.get_message_timer.timeout.connect(self.get_message)
        self.get_message_timer.start()
        # Toast
        self.toast = None

    def get_message(self):
        if not MESSAGE_QUEUE.empty():
            self.toast = ChatToast(MESSAGE_QUEUE.get_nowait())
            self.toast.showFullScreen()

    def close(self) -> bool:
        self.deleteLater()
        self.get_message_timer.stop()
        return super().close()
