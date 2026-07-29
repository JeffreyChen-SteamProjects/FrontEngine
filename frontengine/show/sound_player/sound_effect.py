from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtWidgets import QWidget, QMessageBox

from frontengine.show.window_helpers import apply_overlay_window_flags, load_overlay_icon
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class SoundEffectWidget(QWidget):
    """
    SoundEffectWidget: 播放音效的自訂元件
    SoundEffectWidget: A custom widget for playing sound effects
    """

    def __init__(self, sound_path: str):
        front_engine_logger.info(f"[SoundEffectWidget] Init | sound_path={sound_path}")
        super().__init__()

        self.volume: float = 1.0
        self.sound_player: QSoundEffect = QSoundEffect()
        self.sound_path: Path = Path(sound_path)

        apply_overlay_window_flags(self, show_on_bottom=False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        if self.sound_path.exists() and self.sound_path.is_file():
            source = QUrl.fromLocalFile(str(self.sound_path))
            front_engine_logger.info(f"[SoundEffectWidget] Loading sound file: {self.sound_path}")
            self.sound_player.setSource(source)
            # setLoopCount 只吃 int，直接餵 Loop.Infinite 這個 enum 會 TypeError
            # setLoopCount takes an int only; handing it the Loop.Infinite enum
            # raises TypeError.
            self.sound_player.setLoopCount(QSoundEffect.Loop.Infinite.value)
            self.sound_player.play()
        else:
            front_engine_logger.error(f"[SoundEffectWidget] File not found: {self.sound_path}")
            message_box = QMessageBox(self)
            message_box.setText(
                language_wrapper.language_word_dict.get("sound_effect_message_box_text")
            )
            message_box.show()

        load_overlay_icon(self)

    def set_sound_effect_variable(self, volume: float = 1.0) -> None:
        front_engine_logger.info(f"[SoundEffectWidget] set_sound_effect_variable | volume={volume}")
        self.volume = max(0.0, min(volume, 1.0))
        self.sound_player.setVolume(self.volume)

    def set_muted(self, muted: bool) -> None:
        front_engine_logger.info(f"[SoundEffectWidget] set_muted | muted={muted}")
        self.sound_player.setMuted(bool(muted))

    def closeEvent(self, event) -> None:
        front_engine_logger.info(f"[SoundEffectWidget] closeEvent | event={event}")
        self.sound_player.stop()
        super().closeEvent(event)
