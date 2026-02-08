from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QPixmap, QImage
from PySide6.QtWidgets import QWidget, QGridLayout, QSlider, QLabel, QPushButton, QMessageBox, QCheckBox, QDialog, \
    QComboBox

from frontengine.show.particle.particle_ui import ParticleOpenGLWidget
from frontengine.ui.dialog.choose_file_dialog import choose_image
from frontengine.ui.page.utils import create_monitor_selection_dialog
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class ParticleSettingUI(QWidget):
    def __init__(self):
        front_engine_logger.info("[ParticleSettingUI] Init")
        super().__init__()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # Init variable
        self.particle_list = []
        self.show_all_screen = False
        self.ready_to_play = False
        self.image_path: Optional[str] = None

        # Opacity setting
        self.opacity_label = QLabel(language_wrapper.language_word_dict.get("Opacity"))
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(1, 100)
        self.opacity_slider.setValue(20)
        self.opacity_slider_value_label = QLabel(str(self.opacity_slider.value()))
        self.opacity_slider.valueChanged.connect(self.opacity_trick)

        # Choose file button
        self.choose_file_button = QPushButton(language_wrapper.language_word_dict.get("image_setting_choose_file"))
        self.choose_file_button.clicked.connect(self.choose_and_copy_file_to_cwd_image_dir_then_play)

        # Ready label
        self.ready_label = QLabel(language_wrapper.language_word_dict.get("Not Ready"))

        # Direction
        self.choose_direction_label = QLabel(language_wrapper.language_word_dict.get("choose_particle_direction"))
        self.choose_direction_combobox = QComboBox()
        self.choose_direction_combobox.addItems(
            ["down", "up", "left", "right"]
        )

        # Particle size
        self.particle_size_label = QLabel(language_wrapper.language_word_dict.get("particle_size"))
        self.particle_size_combobox = QComboBox()
        for size in range(10, 310, 10):
            self.particle_size_combobox.addItem(str(size))
        self.particle_size_combobox.setCurrentText("50")

        # Particle count
        self.particle_count_label = QLabel(language_wrapper.language_word_dict.get("particle_count"))
        self.particle_count_combobox = QComboBox()
        for count in range(50, 10010, 10):
            self.particle_count_combobox.addItem(str(count))
        self.particle_count_combobox.setCurrentText("100")

        # Particle speed
        self.particle_speed_label = QLabel(language_wrapper.language_word_dict.get("particle_speed"))
        self.particle_speed_combobox = QComboBox()
        for speed in range(3, 11):
            self.particle_speed_combobox.addItem(str(speed / 1000))

        # Start button
        self.start_button = QPushButton(language_wrapper.language_word_dict.get("particle_setting_ui_play"))
        self.start_button.clicked.connect(self.start_play_particle)

        # Checkboxes
        self.show_on_all_screen_checkbox = QCheckBox(language_wrapper.language_word_dict.get("Show on all screen"))
        self.show_on_all_screen_checkbox.clicked.connect(self.set_show_all_screen)

        # Layout
        self.grid_layout.addWidget(self.opacity_label, 0, 0)
        self.grid_layout.addWidget(self.opacity_slider_value_label, 0, 1)
        self.grid_layout.addWidget(self.opacity_slider, 0, 2)
        self.grid_layout.addWidget(self.choose_file_button, 1, 0)
        self.grid_layout.addWidget(self.ready_label, 1, 1)
        self.grid_layout.addWidget(self.choose_direction_label, 2, 0)
        self.grid_layout.addWidget(self.choose_direction_combobox, 2, 1)
        self.grid_layout.addWidget(self.particle_size_label, 3, 0)
        self.grid_layout.addWidget(self.particle_size_combobox, 3, 1)
        self.grid_layout.addWidget(self.particle_count_label, 4, 0)
        self.grid_layout.addWidget(self.particle_count_combobox, 4, 1)
        self.grid_layout.addWidget(self.particle_speed_label, 5, 0)
        self.grid_layout.addWidget(self.particle_speed_combobox, 5, 1)
        self.grid_layout.addWidget(self.start_button, 6, 0)
        self.grid_layout.addWidget(self.show_on_all_screen_checkbox, 6, 1)

    def set_show_all_screen(self) -> None:
        front_engine_logger.info("[ParticleSettingUI] set_show_all_screen")
        self.show_all_screen = self.show_on_all_screen_checkbox.isChecked()

    def _create_particle_widget(self, screen_width: int = 1920, screen_height: int = 1080) -> ParticleOpenGLWidget:
        front_engine_logger.info("[ParticleSettingUI] _create_particle_widget")
        particle_widget = ParticleOpenGLWidget(
            pixmap=QPixmap(self.image_path),
            particle_size=int(self.particle_size_combobox.currentText()),
            particle_direction=self.choose_direction_combobox.currentText(),
            particle_count=int(self.particle_count_combobox.currentText()),
            opacity=float(self.opacity_slider.value()) / 100,
            screen_width=screen_width,
            screen_height=screen_height,
            particle_speed=float(self.particle_speed_combobox.currentText())
        )
        particle_widget.set_ui_window_flag()
        self.particle_list.append(particle_widget)
        return particle_widget

    def start_play_particle(self) -> None:
        front_engine_logger.info("[ParticleSettingUI] start_play_particle")
        if not self.image_path or not self.ready_to_play:
            message_box = QMessageBox(self)
            message_box.setText(language_wrapper.language_word_dict.get("not_prepare"))
            message_box.exec()  # 改為阻塞
            return

        front_engine_logger.info("[ParticleSettingUI] start play particle")
        monitors = QGuiApplication.screens()

        if not self.show_all_screen and len(monitors) <= 1:
            particle_widget = self._create_particle_widget(
                monitors[0].availableGeometry().width(),
                monitors[0].availableGeometry().height()
            )
            particle_widget.showMaximized()

        elif not self.show_all_screen and len(monitors) >= 2:
            input_dialog, combobox = create_monitor_selection_dialog(self, monitors)
            result = input_dialog.exec()
            if result == QDialog.DialogCode.Accepted:
                select_monitor_index = int(combobox.currentText())
                if len(monitors) > select_monitor_index:
                    monitor = monitors[select_monitor_index]
                    particle_widget = self._create_particle_widget(
                        monitor.availableGeometry().width(),
                        monitor.availableGeometry().height()
                    )
                    particle_widget.setScreen(monitor)
                    particle_widget.move(monitor.availableGeometry().topLeft())
                    particle_widget.showMaximized()

        else:
            for monitor in monitors:
                particle_widget = self._create_particle_widget(
                    monitor.availableGeometry().width(),
                    monitor.availableGeometry().height()
                )
                particle_widget.setScreen(monitor)
                particle_widget.move(monitor.availableGeometry().topLeft())
                particle_widget.showMaximized()

    def choose_and_copy_file_to_cwd_image_dir_then_play(self) -> None:
        front_engine_logger.info("[ParticleSettingUI] choose_and_copy_file_to_cwd_image_dir_then_play")
        self.ready_label.setText(language_wrapper.language_word_dict.get("Not Ready"))
        self.ready_to_play = False
        self.image_path = choose_image(self)
        if self.image_path:
            self.ready_label.setText(language_wrapper.language_word_dict.get("Ready"))
            self.ready_to_play = True

    def opacity_trick(self) -> None:
        front_engine_logger.info("[ParticleSettingUI] opacity_trick")
        self.opacity_slider_value_label.setText(str(self.opacity_slider.value()))