from typing import Union

import pyttsx3
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QBoxLayout, QWidget, QPushButton, QHBoxLayout, QTextEdit, QMessageBox

from frontengine.show.chat.chat_toast import ChatToast
from frontengine.ui.setting.chat.chatthread import MESSAGE_QUEUE, EXCEPTION_QUEUE
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class ChatInputDialog(QWidget):
    def __init__(self, close_time: int = 10000, font_size: int = 16):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
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
        self.get_message_timer.setInterval(1000)
        self.get_message_timer.timeout.connect(self.get_message)
        self.get_message_timer.start()
        # Check error timer
        self.check_error_timer = QTimer()
        self.check_error_timer.setInterval(1000)
        self.check_error_timer.timeout.connect(self.check_error)
        self.check_error_timer.start()
        # Toast
        self.close_time = close_time
        self.font_size = font_size
        self.toast_widget: Union[ChatToast, None] = None
        # Text to speech
        self.engine = pyttsx3.init()

    def get_message(self):
        if not MESSAGE_QUEUE.empty():
            text = MESSAGE_QUEUE.get_nowait()
            self.toast_widget = ChatToast(
                text=text, close_time=self.close_time, font_size=self.font_size)
            self.toast_widget.showFullScreen()
            # self.engine.say(text)

    def show_text(self):
        if self.toast_widget is not None and self.toast_widget.isVisible() is False:
            self.get_message()
        elif self.toast_widget is None:
            self.get_message()

    def check_error(self):
        if not EXCEPTION_QUEUE.empty():
            gpt_error_messagebox = QMessageBox(self)
            gpt_error_messagebox.setText(
                language_wrapper.language_word_dict.get("chat_gpt_exception") + "\n"
                + EXCEPTION_QUEUE.get_nowait()
            )
            gpt_error_messagebox.show()

    def close(self) -> bool:
        self.get_message_timer.stop()
        self.check_error_timer.stop()
        return super().close()
