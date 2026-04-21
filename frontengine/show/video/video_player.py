from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QMessageBox

from frontengine.show.window_helpers import apply_overlay_window_flags, load_overlay_icon
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class VideoWidget(QVideoWidget):
    """
    VideoWidget: 播放影片的自訂元件
    VideoWidget: A custom widget for playing video files
    """

    def __init__(self, video_path: str):
        front_engine_logger.info(f"[VideoWidget] Init | video_path={video_path}")
        super().__init__()

        self.opacity: float = 0.2
        self.volume: float = 1.0
        self.play_rate: float = 1.0
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.media_player: QMediaPlayer = QMediaPlayer()
        self.video_path: Path = Path(video_path)

        if self.video_path.exists() and self.video_path.is_file():
            front_engine_logger.info("[VideoWidget] start_play_video")
            self.audio_output: QAudioOutput = QAudioOutput()
            source = QUrl.fromLocalFile(str(self.video_path))
            front_engine_logger.info(f"[VideoWidget] Loading file: {self.video_path}")
            self.media_player.setSource(source)
            self.media_player.setVideoOutput(self)
            self.media_player.setAudioOutput(self.audio_output)
            self.media_player.errorOccurred.connect(self.video_player_error)
            self.media_player.setLoops(QMediaPlayer.Loops.Infinite)
            self.media_player.play()
        else:
            front_engine_logger.error(f"[VideoWidget] File not found: {self.video_path}")
            message_box = QMessageBox(self)
            message_box.setText(
                language_wrapper.language_word_dict.get("video_player_message_box_text")
            )
            message_box.show()

        load_overlay_icon(self)

    def set_ui_window_flag(self, show_on_bottom: bool = False) -> None:
        front_engine_logger.info(f"[VideoWidget] set_ui_window_flag | show_on_bottom={show_on_bottom}")
        apply_overlay_window_flags(self, show_on_bottom=show_on_bottom)

    def set_ui_variable(self, opacity: float = 0.2) -> None:
        front_engine_logger.info(f"[VideoWidget] set_ui_variable | opacity={opacity}")
        self.opacity = opacity
        self.setWindowOpacity(self.opacity)

    def set_player_variable(self, play_rate: float = 1.0, volume: float = 1.0) -> None:
        front_engine_logger.info(f"[VideoWidget] set_player_variable | play_rate={play_rate}, volume={volume}")
        self.play_rate = play_rate
        self.volume = max(0.0, min(volume, 1.0))
        self.media_player.setPlaybackRate(self.play_rate)
        self.media_player.audioOutput().setVolume(self.volume)

    def closeEvent(self, event) -> None:
        front_engine_logger.info(f"[VideoWidget] closeEvent | event={event}")
        self.media_player.stop()
        super().closeEvent(event)

    def video_player_error(self) -> None:
        error = self.media_player.error()
        front_engine_logger.error(f"[VideoWidget] video_player_error | error={error}")
