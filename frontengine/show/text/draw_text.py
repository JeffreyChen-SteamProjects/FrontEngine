from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QFontDatabase
from PySide6.QtWidgets import QWidget


class TextWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.draw_font = QFontDatabase.font(self.font().family(), "", 200)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setFont(
            self.draw_font
        )
        painter.setPen(Qt.GlobalColor.black)
        painter.setOpacity(0.2)
        painter.drawText(
            QRect(self.x(), self.y(), self.width(), self.height()),
            Qt.AlignmentFlag.AlignCenter,
            "TEST"
        )
        painter.restore()
