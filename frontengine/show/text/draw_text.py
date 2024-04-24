import os
from pathlib import Path

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QFontDatabase, QIcon
from PySide6.QtWidgets import QWidget


class TextWidget(QWidget):

    def __init__(self, text: str, draw_location_x: int = 0, draw_location_y: int = 0,
                 alignment: str = "Center"):
        super().__init__()
        self.draw_location_x = draw_location_x
        self.draw_location_y = draw_location_y
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.text = text
        self.font_size = 100
        self.opacity = 0.2
        if alignment == "TopLeft":
            self.alignment = (Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        elif alignment == "TopRight":
            self.alignment = (Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        elif alignment == "BottomLeft":
            self.alignment = (Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft)
        elif alignment == "BottomRight":
            self.alignment = (Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        else:
            self.alignment = Qt.AlignmentFlag.AlignCenter
        self.draw_font = QFontDatabase.font(self.font().family(), "", self.font_size)
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

    def set_font_variable(self, font_size: int = 100) -> None:
        self.font_size = font_size

    def set_ui_variable(self, opacity: float = 0.2) -> None:
        self.opacity = opacity

    def set_font(self):
        self.draw_font = QFontDatabase.font(self.font().family(), "", self.font_size)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setFont(
            self.draw_font
        )
        painter.setPen(Qt.GlobalColor.black)
        painter.setOpacity(self.opacity)
        painter.drawText(
            QRect(self.draw_location_x, self.draw_location_y, self.width(), self.height()),
            int(self.alignment),
            self.text
        )
        painter.restore()

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        super().mouseDoubleClickEvent(event)

    def mouseGrabber(self) -> None:
        super().mouseGrabber()
