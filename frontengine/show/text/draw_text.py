import os
from pathlib import Path

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QFontDatabase, QIcon
from PySide6.QtWidgets import QWidget


class TextWidget(QWidget):

    def __init__(self, text: str, font_size: int = 100, opacity: float = 0.2):
        super().__init__()
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.text = text
        self.font_size = font_size
        self.opacity = opacity
        self.draw_font = QFontDatabase.font(self.font().family(), "", self.font_size)
        # Set Icon
        self.icon_path = Path(os.getcwd() + "/je_driver_icon.ico")
        if self.icon_path.exists() and self.icon_path.is_file():
            self.setWindowIcon(QIcon(str(self.icon_path)))

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setFont(
            self.draw_font
        )
        painter.setPen(Qt.GlobalColor.black)
        painter.setOpacity(self.opacity)
        painter.drawText(
            QRect(self.x(), self.y(), self.width(), self.height()),
            Qt.AlignmentFlag.AlignCenter,
            self.text
        )
        painter.restore()
