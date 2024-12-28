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

    def __init__(self, video_path: str):
        front_engine_logger.info(f"Init VideoWidget video_path: {video_path}")
        super().__init__()
        self.opacity: float = 0.2
        self.volume: float = 1
        self.play_rate: float = 1
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.media_player = QMediaPlayer()
        self.video_path = Path(video_path)
        if self.video_path.exists() and self.video_path.is_file():
            front_engine_logger.info("start_play_video")
            self.video_file_path = str(self.video_path)
            self.audioOutput = QAudioOutput()
            # QUrl non ascii path encode, Avoid read wrong path and file name
            source = QUrl.fromLocalFile(str(self.video_file_path))
            print(f"Origin file {str(self.video_file_path)}")
            self.media_player.setSource(source)
            self.media_player.setVideoOutput(self)
            self.media_player.setAudioOutput(self.audioOutput)
            self.media_player.errorOccurred.connect(self.video_player_error)
            self.media_player.setLoops(-1)
            self.media_player.play()
        else:
            message_box = QMessageBox(self)
            message_box.setText(
                language_wrapper.language_word_dict.get("video_player_message_box_text")
            )
            message_box.show()
        # Set Icon
        self.icon_path = Path(os.getcwd() + "/je_driver_icon.ico")
        if self.icon_path.exists() and self.icon_path.is_file():
            self.setWindowIcon(QIcon(str(self.icon_path)))


    def set_ui_window_flag(self, show_on_bottom: bool = False) -> None:
        front_engine_logger.info(f"VideoWidget set_ui_window_flag show_on_bottom: {show_on_bottom}")
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowType_Mask |
            Qt.WindowType.Tool
        )
        if not show_on_bottom:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnBottomHint)

    def set_ui_variable(self, opacity: float = 0.2) -> None:
        front_engine_logger.info(f"VideoWidget set_ui_variable opacity: {opacity}")
        self.opacity = opacity
        self.setWindowOpacity(self.opacity)

    def set_player_variable(self, play_rate: float = 1, volume: float = 1) -> None:
        front_engine_logger.info("VideoWidget set_player_variable "
                                 f"play_rate: {play_rate} "
                                 f"volume: {volume}")
        self.play_rate = play_rate
        self.volume = volume
        self.media_player.setPlaybackRate(self.play_rate)
        self.media_player.audioOutput().setVolume(self.volume)

    def closeEvent(self, event) -> None:
        front_engine_logger.info(f"VideoWidget closeEvent event: {event}")
        super().closeEvent(event)
        self.media_player.stop()

    def video_player_error(self) -> None:
        front_engine_logger.info("VideoWidget video_player_error")
        print(self.media_player.error())

    def mousePressEvent(self, event) -> None:
        front_engine_logger.info(f"VideoWidget mousePressEvent event: {event}")
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        front_engine_logger.info(f"VideoWidget mouseDoubleClickEvent event: {event}")
        super().mouseDoubleClickEvent(event)

    def mouseGrabber(self) -> None:
        front_engine_logger.info("VideoWidget mouseGrabber")
        super().mouseGrabber()
