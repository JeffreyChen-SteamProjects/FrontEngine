import os
from pathlib import Path

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QImage, QIcon
from PySide6.QtWidgets import QWidget, QMessageBox

from frontengine.utils.multi_language.language_wrapper import language_wrapper


class ImageWidget(QWidget):

    def __init__(self, image_path: str):
        super().__init__()
        self.opacity = 0.2
        self.image_path = Path(image_path)
        if self.image_path.exists() and self.image_path.is_file():
            print(f"Origin file {str(self.image_path)}")
            self.image = QImage(str(self.image_path))
        else:
            message_box = QMessageBox(self)
            message_box.setText(
                language_wrapper.language_word_dict.get("paint_image_message_box_text")
            )
            message_box.show()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # Set Icon
        self.icon_path = Path(os.getcwd() + "/je_driver_icon.ico")
        if self.icon_path.exists() and self.icon_path.is_file():
            self.setWindowIcon(QIcon(str(self.icon_path)))

    def set_ui_window_flag(self, show_on_bottom: bool = False) -> None:
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        if not show_on_bottom:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnBottomHint)

    def set_ui_variable(self, opacity: float = 0.2):
        self.opacity = opacity

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setOpacity(self.opacity)
        painter.drawImage(
            QRect(self.x(), self.y(), self.width(), self.height()),
            self.image)
        painter.restore()
