from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget


class SceneWidget(QWidget):

    def __init__(self, image_path: str, opacity: float):
        super().__init__()
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )