import os
from pathlib import Path

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QMovie, QPainter, QIcon
from PySide6.QtWidgets import QWidget, QLabel, QMessageBox

from frontengine.utils.multi_language.language_wrapper import language_wrapper


class GifWidget(QWidget):

    def __init__(self, gif_image_path: str, draw_location_x: int = 0, draw_location_y: int = 0):
        super().__init__()
        self.draw_location_x = draw_location_x
        self.draw_location_y = draw_location_y
        self.opacity: float = 0.2
        self.speed: int = 100
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.gif_label: QLabel = QLabel()
        self.gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.movie: QMovie = QMovie()
        self.gif_path = Path(gif_image_path)
        if self.gif_path.exists() and self.gif_path.is_file():
            print(f"Origin file {str(self.gif_path)}")
            self.movie.setFileName(str(self.gif_path))
            self.movie.frameChanged.connect(self.repaint)
            self.gif_label.setMovie(self.movie)
            self.movie.start()
        else:
            message_box: QMessageBox = QMessageBox(self)
            message_box.setText(
                language_wrapper.language_word_dict.get("paint_gif_message_box_text")
            )
            message_box.show()
        # Set Icon
        self.icon_path: Path = Path(os.getcwd() + "/je_driver_icon.ico")
        if self.icon_path.exists() and self.icon_path.is_file():
            self.setWindowIcon(QIcon(str(self.icon_path)))

    def set_gif_variable(self, speed: int = 100) -> None:
        self.speed = speed
        self.movie.setSpeed(self.speed)

    def set_ui_variable(self, opacity: float = 0.2) -> None:
        self.opacity = opacity

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

    def paintEvent(self, event) -> None:
        current_gif_frame = self.movie.currentPixmap()
        painter = QPainter(self)
        painter.setOpacity(self.opacity)
        painter.drawPixmap(
            QRect(
                self.draw_location_x, self.draw_location_y, self.width(), self.height()
            ),
            current_gif_frame
        )
        painter.restore()

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        super().mouseDoubleClickEvent(event)

    def mouseGrabber(self) -> None:
        super().mouseGrabber()

