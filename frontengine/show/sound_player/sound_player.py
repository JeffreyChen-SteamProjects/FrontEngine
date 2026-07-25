from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtWidgets import QWidget, QMessageBox

from frontengine.show.window_helpers import apply_overlay_window_flags, load_overlay_icon
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class SoundPlayer(QWidget):
    """
    SoundPlayer: 播放音樂/音效的自訂元件
    SoundPlayer: A custom widget for playing audio files
    """

    def __init__(self, sound_path: str):
        front_engine_logger.info(f"[SoundPlayer] Init | sound_path={sound_path}")
        super().__init__()

        self.volume: float = 1.0
        self.sound_path: Path = Path(sound_path)

        apply_overlay_window_flags(self, show_on_bottom=False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        if self.sound_path.exists() and self.sound_path.is_file():
            self.media_player: QMediaPlayer = QMediaPlayer()
            self.media_player_audio: QAudioOutput = QAudioOutput()
            self.media_player.setAudioOutput(self.media_player_audio)

            source = QUrl.fromLocalFile(str(self.sound_path))
            front_engine_logger.info(f"[SoundPlayer] Loading file: {self.sound_path}")

            self.media_player.setSource(source)
            self.media_player.setLoops(QMediaPlayer.Loops.Infinite)
            self.media_player.play()
        else:
            front_engine_logger.error(f"[SoundPlayer] File not found: {self.sound_path}")
            message_box = QMessageBox(self)
            message_box.setText(
                language_wrapper.language_word_dict.get("sound_player_message_box_text")
            )
            message_box.show()

        load_overlay_icon(self)

    def set_player_variable(self, volume: float = 1.0) -> None:
        front_engine_logger.info(f"[SoundPlayer] set_player_variable | volume={volume}")
        self.volume = max(0.0, min(volume, 1.0))
        if hasattr(self, "media_player_audio"):
            self.media_player_audio.setVolume(self.volume)

    def set_muted(self, muted: bool) -> None:
        front_engine_logger.info(f"[SoundPlayer] set_muted | muted={muted}")
        if hasattr(self, "media_player_audio"):
            self.media_player_audio.setMuted(bool(muted))

    def closeEvent(self, event) -> None:
        front_engine_logger.info(f"[SoundPlayer] closeEvent | event={event}")
        if hasattr(self, "media_player"):
            self.media_player.stop()
        super().closeEvent(event)
