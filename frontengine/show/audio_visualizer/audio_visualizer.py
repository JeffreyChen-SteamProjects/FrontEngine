import os
from pathlib import Path

from PySide6 import QtQuick
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtWidgets import QWidget, QMessageBox


class AudioPlayer(QWidget):

    def __init__(self, sound_path: str, volume: int = 100):
        super().__init__()
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.media_path = Path(sound_path)
        if self.media_path.exists() and self.media_path.is_file():
            self.media_player = QMediaPlayer()
            self.media_player_audio = QAudioOutput()
            self.media_player.setAudioOutput(self.media_player_audio)
            self.media_player_audio = self.media_player.audioOutput()
            self.media_player.setSource(QUrl.fromLocalFile(str(self.media_path)))
            self.media_player_audio.setVolume(volume)
            self.media_player.setLoops(-1)
            self.media_player.play()
        else:
            message_box = QMessageBox(self)
            message_box.setText("Sound file error")
            message_box.show()
        # Window setting
        self.setWindowTitle("Sound")
        # Set Icon
        self.icon_path = Path(os.getcwd() + "/je_driver_icon.ico")
        if self.icon_path.exists() and self.icon_path.is_file():
            self.setWindowIcon(QIcon(str(self.icon_path)))

    def closeEvent(self, event):
        super().closeEvent(event)
        self.media_player.stop()
