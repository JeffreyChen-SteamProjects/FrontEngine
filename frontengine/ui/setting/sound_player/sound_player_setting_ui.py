import os
import shutil
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QSlider, QPushButton, QFileDialog, QMessageBox

from frontengine.show.sound_player.sound_effect import SoundEffectWidget
from frontengine.show.sound_player.sound_player import SoundPlayer
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class SoundPlayerSettingUI(QWidget):

    def __init__(self):
        super().__init__()
        self.grid_layout = QGridLayout()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        # Init variable
        self.sound_widget_list = list()
        self.show_all_screen = False
        # Volume setting
        self.volume_label = QLabel(
            language_wrapper.language_word_dict.get("Volume")
        )
        self.volume_slider = QSlider()
        self.volume_slider.setMinimum(1)
        self.volume_slider.setMaximum(200)
        self.volume_slider.setTickInterval(1)
        self.volume_slider.setValue(100)
        self.volume_slider_value_label = QLabel(str(self.volume_slider.value()))
        self.volume_slider.setOrientation(Qt.Orientation.Horizontal)
        self.volume_slider.actionTriggered.connect(self.volume_trick)
        # Choose file button
        self.choose_wav_file_button = QPushButton(
            language_wrapper.language_word_dict.get("sound_player_setting_choose_wav_file")
        )
        self.choose_wav_file_button.clicked.connect(self.choose_and_copy_wav_file_to_cwd_sound_dir_then_play)
        # Ready label and variable
        self.wav_ready_label = QLabel(
            language_wrapper.language_word_dict.get("Not Ready")
        )
        self.wav_sound_path: [str, None] = None
        # Choose file button
        self.choose_player_file_button = QPushButton(
            language_wrapper.language_word_dict.get("sound_player_setting_choose_sound_file")
        )
        self.choose_player_file_button.clicked.connect(self.choose_and_copy_sound_file_to_cwd_sound_dir_then_play)
        # Ready label and variable
        self.player_ready_label = QLabel(
            language_wrapper.language_word_dict.get("Not Ready")
        )
        self.player_sound_path: [str, None] = None
        # Start wav button
        self.start_wav_button = QPushButton(
            language_wrapper.language_word_dict.get("sound_player_setting_play_wav")
        )
        self.start_wav_button.clicked.connect(self.start_play_wav)
        # Start button
        self.start_player_button = QPushButton(
            language_wrapper.language_word_dict.get("sound_player_setting_play_sound")
        )
        self.start_player_button.clicked.connect(self.start_play_sound)
        # Add to layout
        self.grid_layout.addWidget(self.volume_label, 0, 0)
        self.grid_layout.addWidget(self.volume_slider_value_label, 0, 1)
        self.grid_layout.addWidget(self.volume_slider, 0, 2)
        self.grid_layout.addWidget(self.choose_wav_file_button, 1, 0)
        self.grid_layout.addWidget(self.wav_ready_label, 1, 1)
        self.grid_layout.addWidget(self.choose_player_file_button, 2, 0)
        self.grid_layout.addWidget(self.player_ready_label, 2, 1)
        self.grid_layout.addWidget(self.start_wav_button, 3, 0)
        self.grid_layout.addWidget(self.start_player_button, 3, 1)
        self.setLayout(self.grid_layout)

    def start_play_wav(self):
        if self.wav_sound_path is None:
            message_box = QMessageBox(self)
            message_box.setText(
                language_wrapper.language_word_dict.get("sound_player_setting_message_box_wav")
            )
            message_box.show()
        else:
            sound_widget = SoundEffectWidget(
                sound_path=self.wav_sound_path,
                volume=self.volume_slider.value()
            )
            self.sound_widget_list.append(sound_widget)
            sound_widget.showFullScreen()

    def start_play_sound(self):
        if self.player_sound_path is None:
            message_box = QMessageBox(self)
            message_box.setText(
                language_wrapper.language_word_dict.get("sound_player_setting_message_box_sound")
            )
            message_box.show()
        else:
            sound_player = SoundPlayer(
                sound_path=self.player_sound_path,
                volume=self.volume_slider.value()
            )
            self.sound_widget_list.append(sound_player)
            sound_player.showFullScreen()

    def choose_and_copy_wav_file_to_cwd_sound_dir_then_play(self):
        file_path = QFileDialog().getOpenFileName(
            parent=self,
            dir=os.getcwd(),
            filter="WAV (*.wav)"
        )[0]
        file_path = Path(file_path)
        self.wav_ready_label.setText(
            language_wrapper.language_word_dict.get("Not Ready")
        )
        if file_path.is_file() and file_path.exists():
            sound_path = Path(str(Path.cwd()) + "/sound")
            if not sound_path.exists() or not sound_path.is_dir():
                sound_path.mkdir(parents=True, exist_ok=True)
            if file_path.suffix.lower() in [".wav"]:
                try:
                    self.wav_sound_path = shutil.copy(file_path, sound_path)
                except shutil.SameFileError:
                    self.wav_sound_path = str(Path(f"{sound_path}/{file_path.name}"))
                self.wav_ready_label.setText(
                    language_wrapper.language_word_dict.get("Ready")
                )
            else:
                message_box = QMessageBox(self)
                message_box.setText(
                    language_wrapper.language_word_dict.get("sound_player_setting_message_box_sound")
                )
                message_box.show()

    def choose_and_copy_sound_file_to_cwd_sound_dir_then_play(self):
        file_path = QFileDialog().getOpenFileName(
            parent=self,
            dir=os.getcwd(),
            filter="Sound (*.mp4;*.mp3;*.wav)"
        )[0]
        file_path = Path(file_path)
        if file_path.is_file() and file_path.exists():
            sound_path = Path(str(Path.cwd()) + "/sound")
            if not sound_path.exists() or not sound_path.is_dir():
                sound_path.mkdir(parents=True, exist_ok=True)
            if file_path.suffix.lower() in [".mp3", ".mp4", ".wav"]:
                try:
                    self.player_sound_path = shutil.copy(file_path, sound_path)
                except shutil.SameFileError:
                    self.player_sound_path = str(Path(f"{sound_path}/{file_path.name}"))
                self.player_ready_label.setText(
                    language_wrapper.language_word_dict.get("Ready")
                )
            else:
                message_box = QMessageBox(self)
                message_box.setText(
                    language_wrapper.language_word_dict.get("sound_player_setting_message_box_sound")
                )
                message_box.show()

    def volume_trick(self):
        self.volume_slider_value_label.setText(str(self.volume_slider.value()))

