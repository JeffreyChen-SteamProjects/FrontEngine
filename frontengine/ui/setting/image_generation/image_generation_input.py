from typing import List

import requests
from PySide6.QtCore import QTimer
from PySide6.QtGui import QPixmap, Qt
from PySide6.QtWidgets import QWidget, QPushButton, QLineEdit, QGridLayout, QMessageBox, QPlainTextEdit

from frontengine.show.image_generation.image_generation_show import ImageGenerateShow
from frontengine.ui.setting.image_generation.generation_image_thread import ImageGenThread, IMAGE_QUEUE
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class ImageGenerationUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        # UI
        self.image_keyword_input = QLineEdit()
        self.send_text_button = QPushButton()
        self.send_text_button.setText(language_wrapper.language_word_dict.get("start_generate_image"))
        self.image_panel = QPlainTextEdit()
        self.image_panel.setReadOnly(True)
        self.send_text_button.clicked.connect(self.generate_image)
        # Layout
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.addWidget(self.image_keyword_input, 0, 0)
        self.grid_layout.addWidget(self.send_text_button, 0, 1)
        self.grid_layout.addWidget(self.image_panel, 1, 0, -1, -1)
        # Pull image timer
        self.pull_image_timer = QTimer()
        self.pull_image_timer.setInterval(1000)
        self.pull_image_timer.timeout.connect(self.get_image)
        self.pull_image_timer.start()
        # Manage show
        self.show_list: List[QWidget] = list()

    def generate_image(self):
        if self.image_keyword_input.text() == "" or self.image_keyword_input.text().isspace():
            input_error_message = QMessageBox(self)
            input_error_message.setText(language_wrapper.language_word_dict.get("input_error"))
            input_error_message.show()
        else:
            image_thread = ImageGenThread(self.image_keyword_input.text())
            image_thread.daemon = True
            image_thread.start()

    def get_image(self):
        if not IMAGE_QUEUE.empty():
            image_link = IMAGE_QUEUE.get_nowait()
            image_response = requests.get(image_link)
            image = QPixmap()
            image.loadFromData(image_response.content)
            image_show = ImageGenerateShow(image, image_link)
            self.show_list.append(image_show)
            image_show.show()
            self.image_panel.appendPlainText(image_link)

    def close(self) -> bool:
        for widget in self.show_list:
            widget.close()
        return super().close()
