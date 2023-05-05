import os
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QSoundEffect
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
        self.sound_player = QSoundEffect()
        self.sound_file_path = Path(os.getcwd() + "/wav_test.wav")
        self.sound_player.setSource(QUrl.fromLocalFile(str(self.sound_file_path)))
        self.sound_player.play()
        print(self.sound_player.isPlaying())

