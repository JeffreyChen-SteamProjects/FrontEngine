import os
import shutil
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QScreen
from PySide6.QtWidgets import QWidget, QGridLayout, QSlider, QLabel, QPushButton, QFileDialog, QMessageBox, \
    QCheckBox

from frontengine.show.image.paint_image import ImageWidget
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class ImageSettingUI(QWidget):

    def __init__(self):
        super().__init__()
        self.grid_layout = QGridLayout()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        # Init variable
        self.image_widget_list = list()
        self.show_all_screen = False
        self.ready_to_play = False
        # Opacity setting
        self.opacity_slider = QSlider()
        self.opacity_slider.setOrientation(Qt.Orientation.Horizontal)
        self.opacity_label = QLabel(
            language_wrapper.language_word_dict.get("Opacity")
        )
        self.opacity_slider.setMinimum(1)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(20)
        self.opacity_slider.setTickInterval(1)
        self.opacity_slider_value_label = QLabel(str(self.opacity_slider.value()))
        self.opacity_slider.actionTriggered.connect(self.opacity_trick)
        self.setLayout(self.grid_layout)
        # Choose file button
        self.choose_file_button = QPushButton(
            language_wrapper.language_word_dict.get("image_setting_choose_file")
        )
        self.choose_file_button.clicked.connect(self.choose_and_copy_file_to_cwd_image_dir_then_play)
        # Ready label and variable
        self.ready_label = QLabel(
            language_wrapper.language_word_dict.get("Not Ready")
        )
        self.gif_image_path: [str, None] = None
        # Start button
        self.start_button = QPushButton(
            language_wrapper.language_word_dict.get("image_setting_ui_play")
        )
        self.start_button.clicked.connect(self.start_play_image)
        # Show on all screen
        self.show_on_all_screen_checkbox = QCheckBox(
            language_wrapper.language_word_dict.get("Show on all screen")
        )
        self.show_on_all_screen_checkbox.clicked.connect(self.set_show_all_screen)
        # Add to layout
        self.grid_layout.addWidget(self.opacity_label, 0, 0)
        self.grid_layout.addWidget(self.opacity_slider_value_label, 0, 1)
        self.grid_layout.addWidget(self.opacity_slider, 0, 2)
        self.grid_layout.addWidget(self.choose_file_button, 1, 0)
        self.grid_layout.addWidget(self.ready_label, 1, 1)
        self.grid_layout.addWidget(self.start_button, 2, 0)
        self.grid_layout.addWidget(self.show_on_all_screen_checkbox, 2, 1)
        self.setLayout(self.grid_layout)

    def set_show_all_screen(self) -> None:
        self.show_all_screen = self.show_on_all_screen_checkbox.isChecked()

    def _create_image_widget(self) -> ImageWidget:
        image_widget = ImageWidget(image_path=self.gif_image_path)
        image_widget.set_ui_variable(opacity=float(self.opacity_slider.value()) / 100)
        self.image_widget_list.append(image_widget)
        return image_widget

    def start_play_image(self) -> None:
        if self.gif_image_path is None or self.ready_to_play is False:
            message_box = QMessageBox(self)
            message_box.setText(
                language_wrapper.language_word_dict.get("not_prepare")
            )
            message_box.show()
        else:
            if self.show_all_screen:
                image_widget = self._create_image_widget()
                image_widget.showFullScreen()
            else:
                monitors = QScreen.virtualSiblings(self.screen())
                for screen in monitors:
                    monitor = screen.availableGeometry()
                    image_widget = self._create_image_widget()
                    image_widget.move(monitor.left(), monitor.top())
                    image_widget.showFullScreen()

    def choose_and_copy_file_to_cwd_image_dir_then_play(self) -> None:
        file_path = QFileDialog().getOpenFileName(
            parent=self,
            dir=os.getcwd(),
            filter="Images (*.png;*.jpg;*.webp)"
        )[0]
        file_path = Path(file_path)
        self.ready_label.setText(
            language_wrapper.language_word_dict.get("Not Ready")
        )
        self.ready_to_play = False
        if file_path.is_file() and file_path.exists():
            image_path = Path(str(Path.cwd()) + "/image")
            if not image_path.exists() or not image_path.is_dir():
                image_path.mkdir(parents=True, exist_ok=True)
            if file_path.suffix.lower() in [
                ".png", ".jpg", ".webp"
            ]:
                try:
                    self.gif_image_path = shutil.copy(file_path, image_path)
                except shutil.SameFileError:
                    self.gif_image_path = str(Path(f"{image_path}/{file_path.name}"))
                self.ready_label.setText(
                    language_wrapper.language_word_dict.get("Ready")
                )
                self.ready_to_play = True
            else:
                message_box = QMessageBox(self)
                message_box.setText(
                    language_wrapper.language_word_dict.get("image_setting_message_box")
                )
                message_box.show()

    def opacity_trick(self) -> None:
        self.opacity_slider_value_label.setText(str(self.opacity_slider.value()))
