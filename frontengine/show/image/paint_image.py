import os
from pathlib import Path

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QImage, QIcon
from PySide6.QtWidgets import QWidget, QMessageBox

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class ImageWidget(QWidget):

    def __init__(self, image_path: str, draw_location_x: int = 0, draw_location_y: int = 0):
        front_engine_logger.info("Init ImageWidget"
                                 f"image_path: {image_path} "
                                 f"draw_location_x: {draw_location_x} "
                                 f" draw_location_y: {draw_location_y}")
        super().__init__()
        self.draw_location_x = draw_location_x
        self.draw_location_y = draw_location_y
        self.opacity: float = 0.2
        self.image_path: Path = Path(image_path)
        if self.image_path.exists() and self.image_path.is_file():
            print(f"Origin file {str(self.image_path)}")
            self.image = QImage(str(self.image_path))
            self.resize(self.image.size())
        else:
            message_box: QMessageBox = QMessageBox(self)
            message_box.setText(
                language_wrapper.language_word_dict.get("paint_image_message_box_text")
            )
            message_box.show()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # Set Icon
        self.icon_path: Path = Path(os.getcwd() + "/je_driver_icon.ico")
        if self.icon_path.exists() and self.icon_path.is_file():
            self.setWindowIcon(QIcon(str(self.icon_path)))

    def set_ui_window_flag(self, show_on_bottom: bool = False) -> None:
        front_engine_logger.info(f"ImageWidget set_ui_window_flag show_on_bottom: {show_on_bottom}")
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        if not show_on_bottom:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnBottomHint)

    def set_ui_variable(self, opacity: float = 0.2) -> None:
        front_engine_logger.info(f"ImageWidget set_ui_variable opacity: {opacity}")
        self.opacity = opacity

    def paintEvent(self, event) -> None:
        front_engine_logger.info(f"ImageWidget paintEvent event: {event}")
        painter = QPainter(self)
        painter.setOpacity(self.opacity)
        painter.drawImage(
            QRect(self.draw_location_x, self.draw_location_y, self.width(), self.height()),
            self.image)
        painter.restore()

    def mousePressEvent(self, event) -> None:
        front_engine_logger.info(f"ImageWidget mousePressEvent event: {event}")
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        front_engine_logger.info(f"ImageWidget mouseDoubleClickEvent event: {event}")
        super().mouseDoubleClickEvent(event)

    def mouseGrabber(self) -> None:
        front_engine_logger.info(f"ImageWidget mouseGrabber")
        super().mouseGrabber()
