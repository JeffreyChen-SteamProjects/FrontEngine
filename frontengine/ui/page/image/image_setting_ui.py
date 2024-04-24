from PySide6.QtCore import Qt
from PySide6.QtGui import QScreen, QGuiApplication
from PySide6.QtWidgets import QWidget, QGridLayout, QSlider, QLabel, QPushButton, QMessageBox, \
    QCheckBox, QDialog

from frontengine.show.image.paint_image import ImageWidget
from frontengine.ui.dialog.choose_file_dialog import choose_image
from frontengine.ui.page.utils import monitor_choose_dialog
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class ImageSettingUI(QWidget):

    def __init__(self):
        super().__init__()
        self.grid_layout = QGridLayout()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
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
        self.image_path: [str, None] = None
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
        # Show on bottom
        self.show_on_bottom_checkbox = QCheckBox(
            language_wrapper.language_word_dict.get("Show on bottom")
        )
        # Add to layout
        self.grid_layout.addWidget(self.opacity_label, 0, 0)
        self.grid_layout.addWidget(self.opacity_slider_value_label, 0, 1)
        self.grid_layout.addWidget(self.opacity_slider, 0, 2)
        self.grid_layout.addWidget(self.choose_file_button, 1, 0)
        self.grid_layout.addWidget(self.ready_label, 1, 1)
        self.grid_layout.addWidget(self.start_button, 2, 0)
        self.grid_layout.addWidget(self.show_on_all_screen_checkbox, 2, 1)
        self.grid_layout.addWidget(self.show_on_bottom_checkbox, 2, 2)
        self.setLayout(self.grid_layout)

    def set_show_all_screen(self) -> None:
        self.show_all_screen = self.show_on_all_screen_checkbox.isChecked()

    def _create_image_widget(self) -> ImageWidget:
        image_widget = ImageWidget(image_path=self.image_path)
        image_widget.set_ui_variable(opacity=float(self.opacity_slider.value()) / 100)
        image_widget.set_ui_window_flag(self.show_on_bottom_checkbox.isChecked())
        self.image_widget_list.append(image_widget)
        return image_widget

    def start_play_image(self) -> None:
        if self.image_path is None or self.ready_to_play is False:
            message_box = QMessageBox(self)
            message_box.setText(
                language_wrapper.language_word_dict.get("not_prepare")
            )
            message_box.show()
        else:
            front_engine_logger.info("start_play_image")
            monitors = QGuiApplication.screens()
            if self.show_all_screen is False and len(monitors) <= 1:
                image_widget = self._create_image_widget()
                image_widget.showFullScreen()
            elif self.show_all_screen is False and len(monitors) >= 2:
                input_dialog, combobox = monitor_choose_dialog(self, monitors)
                result = input_dialog.exec_()
                if result == QDialog.DialogCode.Accepted:
                    select_monitor_index = int(combobox.currentText())
                    if len(monitors) > select_monitor_index:
                        monitor = monitors[select_monitor_index]
                        gif_widget = self._create_image_widget()
                        gif_widget.setScreen(monitor)
                        gif_widget.move(monitor.availableGeometry().topLeft())
                        gif_widget.showFullScreen()
            else:
                for monitor in monitors:
                    image_widget = self._create_image_widget()
                    image_widget.setScreen(monitor)
                    image_widget.move(monitor.availableGeometry().topLeft())
                    image_widget.showFullScreen()

    def choose_and_copy_file_to_cwd_image_dir_then_play(self) -> None:
        self.ready_label.setText(
            language_wrapper.language_word_dict.get("Not Ready")
        )
        self.ready_to_play = False
        self.image_path = choose_image(self)
        if self.image_path is not None:
            self.ready_label.setText(
                language_wrapper.language_word_dict.get("Ready")
            )
            self.ready_to_play = True

    def opacity_trick(self) -> None:
        self.opacity_slider_value_label.setText(str(self.opacity_slider.value()))
