import os
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QSoundEffect, QMediaFormat
from PySide6.QtMultimediaWidgets import QVideoWidget


class VideoWidget(QVideoWidget):

    def __init__(self):
        super().__init__()
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(0.2)
        self.media_player = QMediaPlayer()
        self.sound_player = QSoundEffect()
        self.video_file_path = Path(os.getcwd() + "/test_mp4.mp4")
        self.media_player.setSource(QUrl.fromLocalFile(str(self.video_file_path)))
        self.media_player.setVideoOutput(self)
        self.media_player.setPlaybackRate(1)
        self.media_player.audioOutput().setVolume(100)
        self.media_player.play()

