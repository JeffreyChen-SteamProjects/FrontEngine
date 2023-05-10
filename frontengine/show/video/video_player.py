import os
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QMessageBox


class VideoWidget(QVideoWidget):

    def __init__(self, video_path: str, opacity: float = 0.2,
                 play_rate: float = 1, volume: int = 100
                 ):
        super().__init__()
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground
        )
        self.setWindowOpacity(opacity)
        self.media_player = QMediaPlayer()
        self.video_path = Path(video_path)
        if self.video_path.exists() and self.video_path.is_file():
            self.video_file_path = str(self.video_path)
            self.audioOutput = QAudioOutput()
            source = QUrl.fromLocalFile(str(self.video_file_path).encode())
            source = source.fromEncoded(source.toEncoded())
            self.media_player.setSource(source)
            print(self.media_player.source())
            self.media_player.setVideoOutput(self)
            self.media_player.setAudioOutput(self.audioOutput)
            self.media_player.errorOccurred.connect(self.video_player_error)
            self.media_player.setPlaybackRate(play_rate)
            self.media_player.audioOutput().setVolume(volume)
            self.media_player.setLoops(-1)
            self.media_player.play()
        else:
            message_box = QMessageBox(self)
            message_box.setText("Video error")
            message_box.show()
        self.setWindowTitle("Video")
        # Set Icon
        self.icon_path = Path(os.getcwd() + "/je_driver_icon.ico")
        if self.icon_path.exists() and self.icon_path.is_file():
            self.setWindowIcon(QIcon(str(self.icon_path)))

    def closeEvent(self, event):
        super().closeEvent(event)
        self.media_player.stop()

    def video_player_error(self):
        print(self.media_player.error())
