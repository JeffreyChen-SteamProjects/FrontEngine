import os
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QWidget


class SoundPlayer(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.media_player = QMediaPlayer()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.sound_file_path = Path(os.getcwd() + "/mp3_test.mp3")
        self.media_player.setSource(QUrl.fromLocalFile(str(self.sound_file_path)))
        self.media_player.play()
