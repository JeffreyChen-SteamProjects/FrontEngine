import os
import shutil
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QScreen
from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QSlider, QPushButton, QFileDialog, QMessageBox

from frontengine.show.gif.paint_gif import GifWidget


class GIFSettingUI(QWidget):

    def __init__(self):
        super().__init__()
        self.grid_layout = QGridLayout()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        # Init variable
        self.gif_widget_list = list()
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
        # Speed setting
        self.speed_label = QLabel("Speed")
        self.speed_slider = QSlider()
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(200)
        self.speed_slider.setTickInterval(1)
        self.speed_slider.setValue(100)
        self.speed_slider_value_label = QLabel(str(self.speed_slider.value()))
        self.speed_slider.setOrientation(Qt.Orientation.Horizontal)
        self.speed_slider.actionTriggered.connect(self.speed_trick)
        # Choose file button
        self.choose_file_button = QPushButton("Choose GIF or WEBP file")
        self.choose_file_button.clicked.connect(self.choose_and_copy_file_to_cwd_gif_dir_then_play)
        # Ready label and variable
        self.ready_label = QLabel("Not Ready yet.")
        self.gif_image_path: [str, None] = None
        # Start button
        self.start_button = QPushButton("Start Play GIF or WEBP")
        self.start_button.clicked.connect(self.start_play_gif)
        # Add to layout
        self.grid_layout.addWidget(self.opacity_label, 0, 0)
        self.grid_layout.addWidget(self.opacity_slider_value_label, 0, 1)
        self.grid_layout.addWidget(self.opacity_slider, 0, 2)
        self.grid_layout.addWidget(self.speed_label, 1, 0)
        self.grid_layout.addWidget(self.speed_slider_value_label, 1, 1)
        self.grid_layout.addWidget(self.speed_slider, 1, 2)
        self.grid_layout.addWidget(self.choose_file_button, 2, 0)
        self.grid_layout.addWidget(self.ready_label, 2, 1)
        self.grid_layout.addWidget(self.start_button, 3, 0)
        self.setLayout(self.grid_layout)
        monitors = QScreen.virtualSiblings(self.screen())
        for screen in monitors:
            if screen is not None:
                print(screen.availableGeometry())

    def start_play_gif(self):
        if self.gif_image_path is None:
            message_box = QMessageBox(self)
            message_box.setText("Please choose a gif or webp")
            message_box.show()
        else:
            gif_widget = GifWidget(
                gif_image_path=self.gif_image_path,
                speed=self.speed_slider.value(),
                opacity=float(self.opacity_slider.value()) / 100
            )
            self.gif_widget_list.append(gif_widget)
            gif_widget.showMaximized()

    def choose_and_copy_file_to_cwd_gif_dir_then_play(self):
        file_path = QFileDialog().getOpenFileName(
            parent=self,
            dir=os.getcwd(),
            filter="GIF WEBP (*.gif;*.webp)"
        )[0]
        file_path = Path(file_path)
        if file_path.is_file() and file_path.exists():
            gif_dir_path = Path(str(Path.cwd()) + "/gif")
            if not gif_dir_path.exists() or not gif_dir_path.is_dir():
                gif_dir_path.mkdir(parents=True, exist_ok=True)
            if file_path.suffix.lower() in [".gif", ".webp"]:
                try:
                    self.gif_image_path = shutil.copy(file_path, gif_dir_path)
                except shutil.SameFileError:
                    self.gif_image_path = str(Path(f"{gif_dir_path}/{file_path.name}"))
                self.ready_label.setText("Ready")
            else:
                message_box = QMessageBox(self)
                message_box.setText("Please choose a gif or webp")
                message_box.show()

    def opacity_trick(self):
        self.opacity_slider_value_label.setText(str(self.opacity_slider.value()))

    def speed_trick(self):
        self.speed_slider_value_label.setText(str(self.speed_slider.value()))

