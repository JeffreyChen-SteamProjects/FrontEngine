from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QSlider, QPushButton, QMessageBox, \
    QCheckBox, QDialog

from frontengine.show.gif.paint_gif import GifWidget
from frontengine.ui.dialog.choose_file_dialog import choose_gif
from frontengine.ui.page.utils import monitor_choose_dialog
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class GIFSettingUI(QWidget):

    def __init__(self):
        super().__init__()
        self.grid_layout = QGridLayout()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        # Init variable
        self.gif_widget_list = list()
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
        # Speed setting
        self.speed_label = QLabel(
            language_wrapper.language_word_dict.get("Speed")
        )
        self.speed_slider = QSlider()
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(200)
        self.speed_slider.setTickInterval(1)
        self.speed_slider.setValue(100)
        self.speed_slider_value_label = QLabel(str(self.speed_slider.value()))
        self.speed_slider.setOrientation(Qt.Orientation.Horizontal)
        self.speed_slider.actionTriggered.connect(self.speed_trick)
        # Choose file button
        self.choose_file_button = QPushButton(
            language_wrapper.language_word_dict.get("gif_setting_ui_choose_file")
        )
        self.choose_file_button.clicked.connect(self.choose_and_copy_file_to_cwd_gif_dir_then_play)
        # Ready label and variable
        self.ready_label = QLabel(
            language_wrapper.language_word_dict.get("Not Ready")
        )
        self.gif_image_path: [str, None] = None
        # Start button
        self.start_button = QPushButton(
            language_wrapper.language_word_dict.get("gif_setting_ui_play")
        )
        self.start_button.clicked.connect(self.start_play_gif)
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
        self.grid_layout.addWidget(self.speed_label, 1, 0)
        self.grid_layout.addWidget(self.speed_slider_value_label, 1, 1)
        self.grid_layout.addWidget(self.speed_slider, 1, 2)
        self.grid_layout.addWidget(self.choose_file_button, 2, 0)
        self.grid_layout.addWidget(self.ready_label, 2, 1)
        self.grid_layout.addWidget(self.start_button, 3, 0)
        self.grid_layout.addWidget(self.show_on_all_screen_checkbox, 3, 1)
        self.grid_layout.addWidget(self.show_on_bottom_checkbox, 3, 2)
        self.setLayout(self.grid_layout)

    def set_show_all_screen(self) -> None:
        self.show_all_screen = self.show_on_all_screen_checkbox.isChecked()

    def _create_gif_widget(self) -> GifWidget:
        gif_widget = GifWidget(gif_image_path=self.gif_image_path)
        gif_widget.set_gif_variable(speed=self.speed_slider.value())
        gif_widget.set_ui_variable(opacity=float(self.opacity_slider.value()) / 100)
        gif_widget.set_ui_window_flag(show_on_bottom=self.show_on_bottom_checkbox.isChecked())
        self.gif_widget_list.append(gif_widget)
        return gif_widget

    def start_play_gif(self) -> None:
        if self.gif_image_path is None or self.ready_to_play is False:
            message_box = QMessageBox(self)
            message_box.setText(
                language_wrapper.language_word_dict.get("not_prepare")
            )
            message_box.show()
        else:
            front_engine_logger.info("start_play_gif")
            monitors = QGuiApplication.screens()
            if self.show_all_screen is False and len(monitors) <= 1:
                gif_widget = self._create_gif_widget()
                gif_widget.showFullScreen()
            elif self.show_all_screen is False and len(monitors) >= 2:
                input_dialog, combobox = monitor_choose_dialog(self, monitors)
                result = input_dialog.exec_()
                if result == QDialog.DialogCode.Accepted:
                    select_monitor_index = int(combobox.currentText())
                    if len(monitors) > select_monitor_index:
                        monitor = monitors[select_monitor_index]
                        gif_widget = self._create_gif_widget()
                        gif_widget.setScreen(monitor)
                        gif_widget.move(monitor.availableGeometry().topLeft())
                        gif_widget.showFullScreen()
            else:
                for monitor in monitors:
                    gif_widget = self._create_gif_widget()
                    gif_widget.setScreen(monitor)
                    gif_widget.move(monitor.availableGeometry().topLeft())
                    gif_widget.showFullScreen()

    def choose_and_copy_file_to_cwd_gif_dir_then_play(self) -> None:
        self.ready_label.setText(
            language_wrapper.language_word_dict.get("Not Ready")
        )
        self.ready_to_play = False
        self.gif_image_path = choose_gif(self)
        if self.gif_image_path is not None:
            self.ready_label.setText(
                language_wrapper.language_word_dict.get("Ready")
            )
            self.ready_to_play = True

    def opacity_trick(self) -> None:
        self.opacity_slider_value_label.setText(str(self.opacity_slider.value()))

    def speed_trick(self) -> None:
        self.speed_slider_value_label.setText(str(self.speed_slider.value()))
