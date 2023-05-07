import os
import shutil
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QSlider, QLabel, QPushButton, QMessageBox, QFileDialog

from frontengine.show.video.video_player import VideoWidget


class VideoSettingUI(QWidget):

    def __init__(self):
        super().__init__()
        self.grid_layout = QGridLayout()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        # Init variable
        self.video_widget_list = list()
        self.show_all_screen = False
        # Opacity setting
        self.opacity_slider = QSlider()
        self.opacity_slider.setOrientation(Qt.Orientation.Horizontal)
        self.opacity_label = QLabel("Opacity")
        self.opacity_slider.setMinimum(1)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(20)
        self.opacity_slider.setTickInterval(1)
        self.opacity_slider_value_label = QLabel(str(self.opacity_slider.value()))
        self.opacity_slider.actionTriggered.connect(self.opacity_trick)
        # Play rate setting
        self.play_rate_label = QLabel("Play rate")
        self.play_rate_slider = QSlider()
        self.play_rate_slider.setMinimum(100)
        self.play_rate_slider.setMaximum(200)
        self.play_rate_slider.setTickInterval(1)
        self.play_rate_slider.setValue(100)
        self.play_rate_slider_value_label = QLabel(str(self.play_rate_slider.value()))
        self.play_rate_slider.setOrientation(Qt.Orientation.Horizontal)
        self.play_rate_slider.actionTriggered.connect(self.play_rate_trick)
        # Volume setting
        self.volume_label = QLabel("Volume")
        self.volume_slider = QSlider()
        self.volume_slider.setMinimum(100)
        self.volume_slider.setMaximum(200)
        self.volume_slider.setTickInterval(1)
        self.volume_slider.setValue(100)
        self.volume_slider_value_label = QLabel(str(self.volume_slider.value()))
        self.volume_slider.setOrientation(Qt.Orientation.Horizontal)
        self.volume_slider.actionTriggered.connect(self.volume_trick)
        # Ready label and variable
        self.ready_label = QLabel("Not Ready yet.")
        self.video_path: [str, None] = None
        # Choose file button
        self.choose_file_button = QPushButton("Choose video file")
        self.choose_file_button.clicked.connect(self.choose_and_copy_file_to_cwd_gif_dir_then_play)
        # Start button
        self.start_button = QPushButton("Start Play Video")
        self.start_button.clicked.connect(self.start_play_gif)
        # Add to layout
        self.grid_layout.addWidget(self.opacity_label, 0, 0)
        self.grid_layout.addWidget(self.opacity_slider_value_label, 0, 1)
        self.grid_layout.addWidget(self.opacity_slider, 0, 2)
        self.grid_layout.addWidget(self.play_rate_label, 1, 0)
        self.grid_layout.addWidget(self.play_rate_slider_value_label, 1, 1)
        self.grid_layout.addWidget(self.play_rate_slider, 1, 2)
        self.grid_layout.addWidget(self.volume_label, 2, 0)
        self.grid_layout.addWidget(self.volume_slider_value_label, 2, 1)
        self.grid_layout.addWidget(self.volume_slider, 2, 2)
        self.grid_layout.addWidget(self.choose_file_button, 3, 0)
        self.grid_layout.addWidget(self.start_button, 4, 0)
        self.grid_layout.addWidget(self.ready_label, 4, 1)
        self.setLayout(self.grid_layout)

    def start_play_gif(self):
        if self.video_path is None:
            message_box = QMessageBox(self)
            message_box.setText("Please choose a video file")
            message_box.show()
        else:
            video_widget = VideoWidget(
                self.video_path,
                float(self.opacity_slider.value()) / 100,
                float(self.play_rate_slider.value()) / 100,
                self.volume_slider.value()
            )
            self.video_widget_list.append(video_widget)
            video_widget.showMaximized()

    def choose_and_copy_file_to_cwd_gif_dir_then_play(self):
        file_path = QFileDialog().getOpenFileName(
            parent=self,
            dir=os.getcwd(),
            filter=" Video (*.mp4;)"
        )[0]
        file_path = Path(file_path)
        if file_path.is_file() and file_path.exists():
            video_path = Path(str(Path.cwd()) + "/video")
            if not video_path.exists() or not video_path.is_dir():
                video_path.mkdir(parents=True, exist_ok=True)
            if file_path.suffix.lower() in [".mp4"]:
                try:
                    self.video_path = shutil.copy(file_path, video_path)
                except shutil.SameFileError:
                    self.video_path = str(Path(f"{video_path}/{file_path.name}"))
                self.ready_label.setText("Ready")
            else:
                message_box = QMessageBox(self)
                message_box.setText("Please choose a gif or webp")
                message_box.show()

    def opacity_trick(self):
        self.opacity_slider_value_label.setText(str(self.opacity_slider.value()))

    def play_rate_trick(self):
        self.play_rate_slider_value_label.setText(str(self.play_rate_slider.value()))

    def volume_trick(self):
        self.volume_slider_value_label.setText(str(self.volume_slider.value()))

