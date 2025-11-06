from pathlib import Path

from PySide6.QtCore import QRect
from PySide6.QtGui import QPainter, QImage
from PySide6.QtWidgets import QMessageBox

from frontengine.show.base_widget import BaseWidget
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class ImageWidget(BaseWidget):
    """
    ImageWidget: 顯示靜態圖片
    ImageWidget: Display static image
    """

    def __init__(self, image_path: str, draw_location_x: int = 0, draw_location_y: int = 0):
        super().__init__(draw_location_x, draw_location_y)
        self.image_path: Path = Path(image_path)

        if self.image_path.exists() and self.image_path.is_file():
            front_engine_logger.info(f"Loading image file: {self.image_path}")
            self.image: QImage = QImage(str(self.image_path))
            self.resize(self.image.size())
        else:
            message_box: QMessageBox = QMessageBox(self)
            message_box.setText(language_wrapper.language_word_dict.get("paint_image_message_box_text"))
            message_box.show()

    def draw_content(self, painter: QPainter) -> None:
        painter.drawImage(
            QRect(self.draw_location_x, self.draw_location_y, self.width(), self.height()),
            self.image
        )
