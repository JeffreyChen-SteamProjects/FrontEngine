import os
from pathlib import Path

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QImage
from PySide6.QtWidgets import QWidget, QMessageBox


class ImageWidget(QWidget):

    def __init__(self, image_path: str, opacity: float):
        super().__init__()
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.image_path = Path(image_path)
        if self.image_path.exists() and self.image_path.is_file():
            self.image = QImage(str(self.image_path))
        else:
            message_box = QMessageBox(self)
            message_box.setText("Image Error")
            message_box.show()
        self.opacity = opacity
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # Window setting
        self.setWindowTitle("Image")
        # Set Icon
        self.icon_path = Path(os.getcwd() + "/je_driver_icon.ico")

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setOpacity(self.opacity)
        painter.drawImage(
            QRect(self.x(), self.y(), self.width(), self.height()),
            self.image)
        painter.restore()
