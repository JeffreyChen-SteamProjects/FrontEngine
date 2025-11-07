import os
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QMessageBox

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class VideoWidget(QVideoWidget):
    """
    VideoWidget: 播放影片的自訂元件
    VideoWidget: A custom widget for playing video files
    """

    def __init__(self, video_path: str):
        """
        初始化影片播放器
        Initialize video player

        :param video_path: 影片檔案路徑 / Path to the video file
        """
        front_engine_logger.info(f"[VideoWidget] Init | video_path={video_path}")
        super().__init__()

        # --- 基本屬性 / Basic attributes ---
        self.opacity: float = 0.2
        self.volume: float = 1.0
        self.play_rate: float = 1.0
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.media_player: QMediaPlayer = QMediaPlayer()
        self.video_path: Path = Path(video_path)

        # --- 載入影片 / Load video ---
        if self.video_path.exists() and self.video_path.is_file():
            front_engine_logger.info("[VideoWidget] start_play_video")
            self.audio_output: QAudioOutput = QAudioOutput()

            # QUrl non-ascii path encode, 避免路徑錯誤
            source = QUrl.fromLocalFile(str(self.video_path))
            front_engine_logger.info(f"[VideoWidget] Loading file: {self.video_path}")

            self.media_player.setSource(source)
            self.media_player.setVideoOutput(self)
            self.media_player.setAudioOutput(self.audio_output)
            self.media_player.errorOccurred.connect(self.video_player_error)
            self.media_player.setLoops(QMediaPlayer.Loops.Infinite)  # 無限循環播放
            self.media_player.play()
        else:
            front_engine_logger.error(f"[VideoWidget] File not found: {self.video_path}")
            message_box = QMessageBox(self)
            message_box.setText(
                language_wrapper.language_word_dict.get("video_player_message_box_text")
            )
            message_box.show()

        # --- 設定視窗 Icon / Set window icon ---
        self.icon_path: Path = Path(os.getcwd()) / "je_driver_icon.ico"
        if self.icon_path.exists() and self.icon_path.is_file():
            self.setWindowIcon(QIcon(str(self.icon_path)))

    def set_ui_window_flag(self, show_on_bottom: bool = False) -> None:
        """
        設定視窗旗標 (保持最上層或最下層)
        Set window flags (stay on top or bottom)
        """
        front_engine_logger.info(f"[VideoWidget] set_ui_window_flag | show_on_bottom={show_on_bottom}")
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        if not show_on_bottom:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnBottomHint)

    def set_ui_variable(self, opacity: float = 0.2) -> None:
        """
        設定透明度
        Set opacity
        """
        front_engine_logger.info(f"[VideoWidget] set_ui_variable | opacity={opacity}")
        self.opacity = opacity
        self.setWindowOpacity(self.opacity)

    def set_player_variable(self, play_rate: float = 1.0, volume: float = 1.0) -> None:
        """
        設定播放速度與音量
        Set playback rate and volume
        """
        front_engine_logger.info(f"[VideoWidget] set_player_variable | play_rate={play_rate}, volume={volume}")
        self.play_rate = play_rate
        self.volume = max(0.0, min(volume, 1.0))  # 限制範圍 / Clamp between 0.0 and 1.0
        self.media_player.setPlaybackRate(self.play_rate)
        self.media_player.audioOutput().setVolume(self.volume)

    def closeEvent(self, event) -> None:
        """
        視窗關閉事件：停止播放
        Window close event: stop playback
        """
        front_engine_logger.info(f"[VideoWidget] closeEvent | event={event}")
        self.media_player.stop()
        super().closeEvent(event)

    def video_player_error(self) -> None:
        """
        錯誤處理
        Handle video player errors
        """
        error = self.media_player.error()
        front_engine_logger.error(f"[VideoWidget] video_player_error | error={error}")

    def mousePressEvent(self, event) -> None:
        front_engine_logger.debug(f"[VideoWidget] mousePressEvent | event={event}")
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        front_engine_logger.debug(f"[VideoWidget] mouseDoubleClickEvent | event={event}")
        super().mouseDoubleClickEvent(event)

    def mouseGrabber(self) -> None:
        front_engine_logger.debug("[VideoWidget] mouseGrabber")
        super().mouseGrabber()