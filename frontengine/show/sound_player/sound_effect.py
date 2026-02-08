import os
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtWidgets import QWidget, QMessageBox

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class SoundEffectWidget(QWidget):
    """
    SoundEffectWidget: 播放音效的自訂元件
    SoundEffectWidget: A custom widget for playing sound effects
    """

    def __init__(self, sound_path: str):
        """
        初始化音效元件
        Initialize sound effect widget

        :param sound_path: 音效檔案路徑 / Path to the sound file
        """
        front_engine_logger.info(f"[SoundEffectWidget] Init | sound_path={sound_path}")
        super().__init__()

        # --- 基本屬性 / Basic attributes ---
        self.volume: float = 1.0
        self.sound_player: QSoundEffect = QSoundEffect()
        self.sound_path: Path = Path(sound_path)

        # 設定視窗旗標 / Set window flags
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # --- 載入音效檔案 / Load sound file ---
        if self.sound_path.exists() and self.sound_path.is_file():
            source = QUrl.fromLocalFile(str(self.sound_path))
            front_engine_logger.info(f"[SoundEffectWidget] Loading sound file: {self.sound_path}")
            self.sound_player.setSource(source)
            self.sound_player.setLoopCount(QSoundEffect.Infinite)  # -2 等價於無限循環
            self.sound_player.play()
        else:
            front_engine_logger.error(f"[SoundEffectWidget] File not found: {self.sound_path}")
            message_box = QMessageBox(self)
            message_box.setText(
                language_wrapper.language_word_dict.get("sound_effect_message_box_text")
            )
            message_box.show()

        # --- 設定視窗 Icon / Set window icon ---
        self.icon_path: Path = Path(os.getcwd()) / "frontengine.ico"
        if self.icon_path.exists() and self.icon_path.is_file():
            self.setWindowIcon(QIcon(str(self.icon_path)))

    def set_sound_effect_variable(self, volume: float = 1.0) -> None:
        """
        設定音效音量
        Set sound effect volume

        :param volume: 音量 (0.0 ~ 1.0) / Volume (0.0 ~ 1.0)
        """
        front_engine_logger.info(f"[SoundEffectWidget] set_sound_effect_variable | volume={volume}")
        self.volume = max(0.0, min(volume, 1.0))  # 限制範圍 / Clamp between 0.0 and 1.0
        self.sound_player.setVolume(self.volume)

    def closeEvent(self, event) -> None:
        """
        視窗關閉事件：停止播放音效
        Window close event: stop sound playback
        """
        front_engine_logger.info(f"[SoundEffectWidget] closeEvent | event={event}")
        self.sound_player.stop()
        super().closeEvent(event)
