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
        # 先給一張空圖，路徑失效時 paintEvent 才不會撞上未定義的屬性
        # Start from an empty image so a bad path cannot leave paintEvent
        # facing an attribute that was never assigned.
        self.image: QImage = QImage()

        if self.image_path.exists() and self.image_path.is_file():
            front_engine_logger.info(f"Loading image file: {self.image_path}")
            self.image = QImage(str(self.image_path))
            self.resize(self.image.size())
        else:
            message_box: QMessageBox = QMessageBox(self)
            message_box.setText(language_wrapper.language_word_dict.get("paint_image_message_box_text"))
            message_box.show()

    def set_image_path(self, image_path: str) -> bool:
        """
        熱換顯示的圖片（用於輪播）。路徑無效時保持原圖並回傳 False。
        Hot-swap the displayed image (used by the slideshow). Keeps the
        current image and returns False when the path is invalid.
        """
        path = Path(image_path)
        if not (path.exists() and path.is_file()):
            front_engine_logger.warning(f"[ImageWidget] set_image_path skip invalid: {path}")
            return False
        self.image_path = path
        self.image = QImage(str(path))
        self.resize(self.image.size())
        self.update()
        return True

    def draw_content(self, painter: QPainter) -> None:
        if self.image.isNull():
            return
        painter.drawImage(
            QRect(self.draw_location_x, self.draw_location_y, self.width(), self.height()),
            self.image
        )
