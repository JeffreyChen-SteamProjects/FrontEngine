import os
from pathlib import Path

from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtGui import QPainter, QImage
from PySide6.QtWidgets import QWidget


class ImageWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.image_path = Path(os.getcwd() + "/tt.jpg")
        self.image = QImage(str(self.image_path))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setOpacity(0.20)
        painter.drawImage(
            QRect(self.x(), self.y(), self.width(), self.height()),
            self.image)
        painter.restore()
