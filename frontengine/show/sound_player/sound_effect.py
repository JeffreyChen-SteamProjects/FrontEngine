import os
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtWidgets import QWidget, QMessageBox

from frontengine.utils.multi_language.language_wrapper import language_wrapper


class SoundEffectWidget(QWidget):

    def __init__(self, sound_path: str):
        super().__init__()
        self.volume: float = 1
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.sound_player = QSoundEffect()
        self.sound_path = Path(sound_path)
        if self.sound_path.exists() and self.sound_path.is_file():
            # QUrl non ascii path encode, Avoid read wrong path and file name
            source = QUrl.fromLocalFile(str(self.sound_path))
            print(f"Origin file {str(self.sound_path)}")
            self.sound_player.setSource(source)
            # -2 means loop forever
            self.sound_player.setLoopCount(-2)
            self.sound_player.play()
        else:
            message_box = QMessageBox(self)
            message_box.setText(
                language_wrapper.language_word_dict.get("sound_effect_message_box_text")
            )
            message_box.show()
        # Set Icon
        self.icon_path = Path(os.getcwd() + "/je_driver_icon.ico")
        if self.icon_path.exists() and self.icon_path.is_file():
            self.setWindowIcon(QIcon(str(self.icon_path)))

    def set_sound_effect_variable(self, volume: float = 1) -> None:
        self.volume = volume
        self.sound_player.setVolume(self.volume)

    def closeEvent(self, event) -> None:
        super().closeEvent(event)
        self.sound_player.stop()
