import sys

from PySide6.QtCore import QPoint
from PySide6.QtGui import Qt, QPainter
from PySide6.QtWidgets import QMainWindow, QApplication, QGridLayout

from background_assistant.ui.main_widget import MainWidget


class AssistantUI(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.main_widget = MainWidget()
        self.setCentralWidget(self.main_widget)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)


def start_assistant():
    new_editor = QApplication(sys.argv)
    window = AssistantUI()
    window.showMaximized()
    sys.exit(new_editor.exec())


start_assistant()
