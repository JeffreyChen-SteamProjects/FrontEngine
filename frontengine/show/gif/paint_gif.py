from pathlib import Path

from PySide6.QtCore import QRect
from PySide6.QtGui import QPainter, QMovie
from PySide6.QtWidgets import QMessageBox, QLabel

from frontengine.show.base_widget import BaseWidget
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class GifWidget(BaseWidget):
    """
    GifWidget: 顯示 GIF 動畫
    GifWidget: Display animated GIF
    """

    def __init__(self, gif_image_path: str, draw_location_x: int = 0, draw_location_y: int = 0):
        super().__init__(draw_location_x, draw_location_y)
        self.speed: int = 100
        self.gif_path: Path = Path(gif_image_path)
        self.movie: QMovie = QMovie()
        self.gif_label: QLabel = QLabel()

        if self.gif_path.exists() and self.gif_path.is_file():
            front_engine_logger.info(f"Loading GIF file: {self.gif_path}")
            self.movie.setFileName(str(self.gif_path))
            self.movie.frameChanged.connect(self.repaint)
            self.gif_label.setMovie(self.movie)
            self.movie.start()
            self.resize(self.movie.frameRect().size())
        else:
            message_box: QMessageBox = QMessageBox(self)
            message_box.setText(language_wrapper.language_word_dict.get("paint_gif_message_box_text"))
            message_box.show()

    def set_gif_variable(self, speed: int = 100) -> None:
        front_engine_logger.info(f"GifWidget set_gif_variable | speed: {speed}")
        self.speed = speed
        self.movie.setSpeed(self.speed)

    def draw_content(self, painter: QPainter) -> None:
        current_gif_frame = self.movie.currentPixmap()
        painter.drawPixmap(
            QRect(self.draw_location_x, self.draw_location_y, self.width(), self.height()),
            current_gif_frame
        )
