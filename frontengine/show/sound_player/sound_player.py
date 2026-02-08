import os
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtWidgets import QWidget, QMessageBox

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class SoundPlayer(QWidget):
    """
    SoundPlayer: 播放音樂/音效的自訂元件
    SoundPlayer: A custom widget for playing audio files
    """

    def __init__(self, sound_path: str):
        """
        初始化音樂播放器
        Initialize the sound player

        :param sound_path: 音檔路徑 / Path to the audio file
        """
        front_engine_logger.info(f"[SoundPlayer] Init | sound_path={sound_path}")
        super().__init__()

        # --- 基本屬性 / Basic attributes ---
        self.volume: float = 1.0
        self.sound_path: Path = Path(sound_path)

        # 設定視窗旗標 / Set window flags
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # --- 初始化播放器 / Initialize media player ---
        if self.sound_path.exists() and self.sound_path.is_file():
            self.media_player: QMediaPlayer = QMediaPlayer()
            self.media_player_audio: QAudioOutput = QAudioOutput()
            self.media_player.setAudioOutput(self.media_player_audio)

            # QUrl non-ascii path encode, 避免路徑錯誤
            source = QUrl.fromLocalFile(str(self.sound_path))
            front_engine_logger.info(f"[SoundPlayer] Loading file: {self.sound_path}")

            self.media_player.setSource(source)
            self.media_player.setLoops(QMediaPlayer.Loops.Infinite)  # 無限循環播放
            self.media_player.play()
        else:
            front_engine_logger.error(f"[SoundPlayer] File not found: {self.sound_path}")
            message_box = QMessageBox(self)
            message_box.setText(
                language_wrapper.language_word_dict.get("sound_player_message_box_text")
            )
            message_box.show()

        # --- 設定視窗 Icon / Set window icon ---
        self.icon_path: Path = Path(os.getcwd()) / "frontengine.ico"
        if self.icon_path.exists() and self.icon_path.is_file():
            self.setWindowIcon(QIcon(str(self.icon_path)))

    def set_player_variable(self, volume: float = 1.0) -> None:
        """
        設定播放器音量
        Set player volume

        :param volume: 音量 (0.0 ~ 1.0) / Volume (0.0 ~ 1.0)
        """
        front_engine_logger.info(f"[SoundPlayer] set_player_variable | volume={volume}")
        self.volume = max(0.0, min(volume, 1.0))  # 限制範圍 / Clamp between 0.0 and 1.0
        if hasattr(self, "media_player_audio"):
            self.media_player_audio.setVolume(self.volume)

    def closeEvent(self, event) -> None:
        """
        視窗關閉事件：停止播放
        Window close event: stop playback
        """
        front_engine_logger.info(f"[SoundPlayer] closeEvent | event={event}")
        if hasattr(self, "media_player"):
            self.media_player.stop()
        super().closeEvent(event)
