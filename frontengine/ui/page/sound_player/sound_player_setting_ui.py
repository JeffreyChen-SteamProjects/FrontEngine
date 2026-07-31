from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QSlider, QPushButton, QMessageBox

from frontengine.show.sound_player.sound_effect import SoundEffectWidget
from frontengine.show.sound_player.sound_player import SoundPlayer
from frontengine.ui.dialog.choose_file_dialog import choose_player_sound, choose_wav_sound
from frontengine.ui.page.layout_kit import SettingPage
from frontengine.ui.page.utils import coerce_int
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import retranslator, tr, translate


# 四處共用的語系鍵
# The language key shared by four call sites.
_NOT_READY = "Not Ready"


class SoundPlayerSettingUI(SettingPage):
    def __init__(self):
        front_engine_logger.info("[SoundPlayerSettingUI] Init")
        super().__init__("tab_sound_text", "page_subtitle_sound",
                         "Sound", "Play a sound or a piece of music.")

        # Init variable
        self.sound_widget_list = []
        # 這一頁有兩個各自獨立的選擇器。共用一個 ready_to_play 的話，在音樂選擇
        # 對話框按下取消會把「WAV 已就緒」一起清掉，明明選好的音效反而變成
        # 「尚未準備」。就緒狀態要跟著各自的路徑走。
        # This page has two independent pickers. Sharing one ready_to_play meant
        # cancelling the music dialog also cleared "the WAV is ready", so a
        # perfectly good sound effect reported itself as not prepared. Readiness
        # belongs to each path.
        self.wav_ready_to_play = False
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
        # 音效與音樂是兩件事，各自有檔案與就緒狀態，所以分成兩列而不是混在一起
        # A sound effect and a piece of music are separate errands with separate
        # files and readiness, so they get a row each rather than one pile.
        source = self.add_section("section_source", "Source")
        source.add_row(self.wav_ready_label, self.choose_wav_file_button)
        source.add_row(self.player_ready_label, self.choose_player_file_button)

        options = self.add_section("section_options", "Options")
        options.add_slider_row(
            self.volume_label, self.volume_slider, self.volume_slider_value_label)

        self.finish_body()
        self.set_footer(primary=self.start_player_button, extra=[self.start_wav_button])

    def start_play_wav(self) -> None:
        front_engine_logger.info("[SoundPlayerSettingUI] start_play_wav")
        if not self.wav_sound_path or not self.wav_ready_to_play:
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
        self.wav_ready_to_play = False
        self.wav_sound_path = choose_wav_sound(self)
        if self.wav_sound_path:
            retranslator.set_text(self.wav_ready_label, "Ready")
            self.wav_ready_to_play = True

    def choose_and_copy_sound_file_to_cwd_sound_dir_then_play(self) -> None:
        front_engine_logger.info("[SoundPlayerSettingUI] choose_and_copy_sound_file_to_cwd_sound_dir_then_play")
        retranslator.set_text(self.player_ready_label, _NOT_READY)
        self.player_sound_path = choose_player_sound(self)
        if self.player_sound_path:
            retranslator.set_text(self.player_ready_label, "Ready")

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
            self.wav_ready_to_play = True
            retranslator.set_text(self.wav_ready_label, "Ready")
        if state.get("player_sound_path"):
            self.player_sound_path = state["player_sound_path"]
            retranslator.set_text(self.player_ready_label, "Ready")