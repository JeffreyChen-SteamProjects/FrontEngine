from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QSlider, QPushButton, QMessageBox

from frontengine.show.sound_player.sound_effect import SoundEffectWidget
from frontengine.show.sound_player.sound_player import SoundPlayer
from frontengine.ui.dialog.choose_file_dialog import choose_player_sound, choose_wav_sound
from frontengine.ui.page.utils import coerce_int
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import retranslator, tr, translate


# 四處共用的語系鍵
# The language key shared by four call sites.
_NOT_READY = "Not Ready"


class SoundPlayerSettingUI(QWidget):
    def __init__(self):
        front_engine_logger.info("[SoundPlayerSettingUI] Init")
        super().__init__()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        # Init variable
        self.sound_widget_list = []
        self.ready_to_play = False
        self.wav_sound_path: Optional[str] = None
        self.player_sound_path: Optional[str] = None

        # Volume setting
        self.volume_label = tr(QLabel(), "Volume")
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(1, 100)
        self.volume_slider.setValue(100)
        self.volume_slider_value_label = QLabel(str(self.volume_slider.value()))
        self.volume_slider.valueChanged.connect(self.volume_trick)

        # Choose WAV file
        self.choose_wav_file_button = tr(QPushButton(), "sound_player_setting_choose_wav_file")
        self.choose_wav_file_button.clicked.connect(self.choose_and_copy_wav_file_to_cwd_sound_dir_then_play)
        self.wav_ready_label = QLabel(translate(_NOT_READY))
        retranslator.bind(self.wav_ready_label, _NOT_READY)

        # Choose general sound file
        self.choose_player_file_button = tr(
            QPushButton(), "sound_player_setting_choose_sound_file",
)
        self.choose_player_file_button.clicked.connect(self.choose_and_copy_sound_file_to_cwd_sound_dir_then_play)
        self.player_ready_label = QLabel(translate(_NOT_READY))
        retranslator.bind(self.player_ready_label, _NOT_READY)

        # Start buttons
        self.start_wav_button = tr(QPushButton(), "sound_player_setting_play_wav")
        self.start_wav_button.clicked.connect(self.start_play_wav)

        self.start_player_button = tr(QPushButton(), "sound_player_setting_play_sound")
        self.start_player_button.clicked.connect(self.start_play_sound)

        # Layout
        self.grid_layout.addWidget(self.volume_label, 0, 0)
        self.grid_layout.addWidget(self.volume_slider_value_label, 0, 1)
        self.grid_layout.addWidget(self.volume_slider, 0, 2)
        self.grid_layout.addWidget(self.choose_wav_file_button, 1, 0)
        self.grid_layout.addWidget(self.wav_ready_label, 1, 1)
        self.grid_layout.addWidget(self.choose_player_file_button, 2, 0)
        self.grid_layout.addWidget(self.player_ready_label, 2, 1)
        self.grid_layout.addWidget(self.start_wav_button, 3, 0)
        self.grid_layout.addWidget(self.start_player_button, 3, 1)

    def start_play_wav(self) -> None:
        front_engine_logger.info("[SoundPlayerSettingUI] start_play_wav")
        if not self.wav_sound_path or not self.ready_to_play:
            message_box = QMessageBox(self)
            message_box.setText(language_wrapper.language_word_dict.get("sound_player_setting_message_box_wav"))
            message_box.exec()
            return

        sound_widget = SoundEffectWidget(sound_path=self.wav_sound_path)
        sound_widget.set_sound_effect_variable(volume=float(self.volume_slider.value()) / 100)
        self.sound_widget_list.append(sound_widget)
        sound_widget.showFullScreen()

    def start_play_sound(self) -> None:
        front_engine_logger.info("[SoundPlayerSettingUI] start_play_sound")
        if not self.player_sound_path:
            message_box = QMessageBox(self)
            message_box.setText(language_wrapper.language_word_dict.get("not_prepare"))
            message_box.exec()
            return

        sound_player = SoundPlayer(sound_path=self.player_sound_path)
        sound_player.set_player_variable(volume=float(self.volume_slider.value()) / 100)
        self.sound_widget_list.append(sound_player)
        sound_player.showFullScreen()

    def choose_and_copy_wav_file_to_cwd_sound_dir_then_play(self) -> None:
        front_engine_logger.info("[SoundPlayerSettingUI] choose_and_copy_wav_file_to_cwd_sound_dir_then_play")
        retranslator.set_text(self.wav_ready_label, _NOT_READY)
        self.ready_to_play = False
        self.wav_sound_path = choose_wav_sound(self)
        if self.wav_sound_path:
            retranslator.set_text(self.wav_ready_label, "Ready")
            self.ready_to_play = True

    def choose_and_copy_sound_file_to_cwd_sound_dir_then_play(self) -> None:
        front_engine_logger.info("[SoundPlayerSettingUI] choose_and_copy_sound_file_to_cwd_sound_dir_then_play")
        retranslator.set_text(self.player_ready_label, _NOT_READY)
        self.ready_to_play = False
        self.player_sound_path = choose_player_sound(self)
        if self.player_sound_path:
            retranslator.set_text(self.player_ready_label, "Ready")
            self.ready_to_play = True

    def volume_trick(self) -> None:
        front_engine_logger.info("[SoundPlayerSettingUI] volume_trick")
        self.volume_slider_value_label.setText(str(self.volume_slider.value()))

    def get_state(self) -> dict:
        return {
            "volume": self.volume_slider.value(),
            "wav_sound_path": self.wav_sound_path,
            "player_sound_path": self.player_sound_path,
        }

    def set_state(self, state: dict) -> None:
        volume = coerce_int(state.get("volume"))
        if volume is not None:
            self.volume_slider.setValue(volume)
        if state.get("wav_sound_path"):
            self.wav_sound_path = state["wav_sound_path"]
            self.ready_to_play = True
            retranslator.set_text(self.wav_ready_label, "Ready")
        if state.get("player_sound_path"):
            self.player_sound_path = state["player_sound_path"]
            retranslator.set_text(self.player_ready_label, "Ready")