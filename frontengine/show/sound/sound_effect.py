from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget


class SoundEffectWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
