from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import QWidget, QGridLayout, QSlider, QLabel, QPushButton, QMessageBox, \
    QCheckBox, QDialog, QComboBox

from frontengine.show.particle.paint_particle import ParticleWidget
from frontengine.ui.dialog.choose_file_dialog import choose_image
from frontengine.ui.page.utils import monitor_choose_dialog
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class ParticleSettingUI(QWidget):

    def __init__(self):
        super().__init__()
        self.grid_layout = QGridLayout()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        # Init variable
        self.particle_list = []
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
        # Choose direction
        self.choose_direction_label = QLabel(language_wrapper.language_word_dict.get("choose_particle_direction"))
        self.choose_direction_combobox = QComboBox()
        self.choose_direction_combobox.addItems(
            ["down", "up", "left", "right", "left_down", "left_up", "right_down", "right_up",
             "random_minus", "random_add", "random"])
        # Particle size
        self.particle_size_label = QLabel(language_wrapper.language_word_dict.get("particle_size"))
        self.particle_size_combobox = QComboBox()
        for size in range(10, 310, 10):
            self.particle_size_combobox.addItem(str(size))
        self.particle_size_combobox.setCurrentText("50")
        # Particle count
        self.particle_count_label = QLabel(language_wrapper.language_word_dict.get("particle_count"))
        self.particle_count_combobox = QComboBox()
        for count in range(50, 1010, 10):
            self.particle_count_combobox.addItem(str(count))
        self.particle_count_combobox.setCurrentText("100")
        # Particle count
        self.particle_speed_label = QLabel(language_wrapper.language_word_dict.get("particle_speed"))
        self.particle_speed_combobox = QComboBox()
        for speed in range(1, 11, 1):
            self.particle_speed_combobox.addItem(str(speed))
        # Start button
        self.start_button = QPushButton(
            language_wrapper.language_word_dict.get("particle_setting_ui_play")
        )
        self.start_button.clicked.connect(self.start_play_particle)
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
        self.grid_layout.addWidget(self.show_on_bottom_checkbox, 6, 2)
        self.setLayout(self.grid_layout)

    def set_show_all_screen(self) -> None:
        self.show_all_screen = self.show_on_all_screen_checkbox.isChecked()

    def _create_particle_widget(self, screen_width: int = 1920, screen_height: int = 1080) -> ParticleWidget:
        particle_widget = ParticleWidget(
            pixmap=QPixmap(self.image_path),
            particle_size=int(self.particle_size_combobox.currentText()),
            particle_direction=self.choose_direction_combobox.currentText(),
            particle_count=int(self.particle_count_combobox.currentText()),
            opacity=float(self.opacity_slider.value()) / 100,
            screen_width=screen_width,
            screen_height=screen_height,
            particle_speed=int(self.particle_speed_combobox.currentText())
        )
        particle_widget.set_ui_window_flag(self.show_on_bottom_checkbox.isChecked())
        self.particle_list.append(particle_widget)
        return particle_widget

    def start_play_particle(self) -> None:
        if self.image_path is None or self.ready_to_play is False:
            message_box = QMessageBox(self)
            message_box.setText(
                language_wrapper.language_word_dict.get("not_prepare")
            )
            message_box.show()
        else:
            front_engine_logger.info("start play particle")
            monitors = QGuiApplication.screens()
            if self.show_all_screen is False and len(monitors) <= 1:
                particle_widget = self._create_particle_widget(
                    monitors[0].availableGeometry().width(),
                    monitors[0].availableGeometry().height()
                )
                particle_widget.showFullScreen()
            elif self.show_all_screen is False and len(monitors) >= 2:
                input_dialog, combobox = monitor_choose_dialog(self, monitors)
                result = input_dialog.exec_()
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
                        particle_widget.showFullScreen()
            else:
                for monitor in monitors:
                    particle_widget = self._create_particle_widget(
                        monitor.availableGeometry().width(),
                        monitor.availableGeometry().height()
                    )
                    particle_widget.setScreen(monitor)
                    particle_widget.move(monitor.availableGeometry().topLeft())
                    particle_widget.showFullScreen()

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
