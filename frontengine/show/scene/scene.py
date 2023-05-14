from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget


class SceneWidget(QWidget):

    def __init__(
            self,
            gif_detail: dict,
            image_detail: dict,
            sound_player_detail: dict,
            text_detail: dict,
            video_detail: dict,
            web_detail: dict
    ):
        super().__init__()
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
