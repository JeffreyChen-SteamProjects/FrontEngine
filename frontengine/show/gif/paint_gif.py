import os
from pathlib import Path

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QMovie, QPainter
from PySide6.QtWidgets import QWidget, QLabel


class GifWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.gif_label = QLabel()
        self.gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.gif_path = Path(os.getcwd() + "/test.gif")
        self.movie = QMovie(str(self.gif_path))
        self.movie.frameChanged.connect(self.repaint)
        self.gif_label.setMovie(self.movie)
        self.movie.start()

    def paintEvent(self, event) -> None:
        current_gif_frame = self.movie.currentPixmap()
        painter = QPainter(self)
        painter.setOpacity(0.2)
        painter.drawPixmap(
            QRect(
                self.x(), self.y(), self.width(), self.height()
            ),
            current_gif_frame
        )
        painter.restore()
