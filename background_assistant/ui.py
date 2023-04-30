import sys

from PySide6.QtCore import QRect
from PySide6.QtGui import Qt, QImage, QPainter, QPalette, QColor, QFontDatabase
from PySide6.QtWidgets import QMainWindow, QApplication, QWidget, QGridLayout, QLabel


class AssistantUI(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.qimg = QImage("../R.png")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.q_widget = QWidget()
        self.grid_layout = QGridLayout(self.q_widget)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(self.q_widget)
        self.palette = QPalette()
        self.palette.setColor(self.palette.ColorGroup.Active, self.palette.ColorRole.Text, QColor(255, 0, 255))
        self.label = QLabel("Test")
        self.label.setFont(
            QFontDatabase.font(
                self.font().family(),
                "",
                50
            )
        )
        self.label.setPalette(self.palette)
        self.grid_layout.addWidget(self.label, 0, 0)

    def paintEvent(self, paint_event):
        painter = QPainter(self)
        painter.setOpacity(0.20)
        painter.drawImage(
            QRect(self.x(), self.y(), self.width(), self.height()),
            self.qimg)
        painter.restore()


def start_assistant():
    new_editor = QApplication(sys.argv)
    window = AssistantUI()
    window.showMaximized()
    sys.exit(new_editor.exec())


start_assistant()
