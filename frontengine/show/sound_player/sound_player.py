import os
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtWidgets import QWidget, QMessageBox

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class SoundPlayer(QWidget):

    def __init__(self, sound_path: str):
        front_engine_logger.info(f"Init SoundPlayer sound_path: {sound_path}")
        super().__init__()
        self.volume: float = 1
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.sound_path = Path(sound_path)
        if self.sound_path.exists() and self.sound_path.is_file():
            self.media_player = QMediaPlayer()
            self.media_player_audio = QAudioOutput()
            self.media_player.setAudioOutput(self.media_player_audio)
            self.media_player_audio = self.media_player.audioOutput()
            # QUrl non ascii path encode, Avoid read wrong path and file name
            source = QUrl.fromLocalFile(str(self.sound_path))
            print(f"Origin file {str(self.sound_path)}")
            self.media_player.setSource(source)
            self.media_player.setLoops(-1)
            self.media_player.play()
        else:
            message_box = QMessageBox(self)
            message_box.setText(
                language_wrapper.language_word_dict.get("sound_player_message_box_text")
            )
            message_box.show()
        # Set Icon
        self.icon_path = Path(os.getcwd() + "/je_driver_icon.ico")
        if self.icon_path.exists() and self.icon_path.is_file():
            self.setWindowIcon(QIcon(str(self.icon_path)))

    def set_player_variable(self, volume: float = 1) -> None:
        front_engine_logger.info(f"SoundPlayer set_player_variable volume: {volume}")
        self.volume = volume
        self.media_player_audio.setVolume(self.volume)

    def closeEvent(self, event) -> None:
        front_engine_logger.info(f"SoundPlayer closeEvent event: {event}")
        super().closeEvent(event)
        self.media_player.stop()
