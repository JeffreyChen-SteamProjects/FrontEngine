from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import QWidget, QGridLayout, QSlider, QLabel, QPushButton, QMessageBox, QCheckBox, QComboBox

from frontengine.show.particle.particle_ui import ParticleOpenGLWidget
from frontengine.ui.dialog.choose_file_dialog import choose_image
from frontengine.ui.page.utils import (
    build_recent_combobox,
    build_target_monitor_combobox,
    coerce_int,
    dispatch_to_monitors,
    enable_file_drop,
    reload_recent_combobox,
    resolve_preferred_monitor,
)
from frontengine.user_setting.user_setting_file import add_recent_file
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import retranslator


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
        retranslator.bind(self.opacity_label, "Opacity", "")
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(1, 100)
        self.opacity_slider.setValue(20)
        self.opacity_slider_value_label = QLabel(str(self.opacity_slider.value()))
        self.opacity_slider.valueChanged.connect(self.opacity_trick)

        # Choose file button
        self.choose_file_button = QPushButton(language_wrapper.language_word_dict.get("image_setting_choose_file"))
        retranslator.bind(self.choose_file_button, "image_setting_choose_file", "")
        self.choose_file_button.clicked.connect(self.choose_and_copy_file_to_cwd_image_dir_then_play)

        # Ready label
        self.ready_label = QLabel(language_wrapper.language_word_dict.get("Not Ready"))
        retranslator.bind(self.ready_label, "Not Ready", "")

        # Direction
        self.choose_direction_label = QLabel(language_wrapper.language_word_dict.get("choose_particle_direction"))
        retranslator.bind(self.choose_direction_label, "choose_particle_direction", "")
        self.choose_direction_combobox = QComboBox()
        self.choose_direction_combobox.addItems(
            ["down", "up", "left", "right"]
        )

        # Particle size
        self.particle_size_label = QLabel(language_wrapper.language_word_dict.get("particle_size"))
        retranslator.bind(self.particle_size_label, "particle_size", "")
        self.particle_size_combobox = QComboBox()
        for size in range(10, 310, 10):
            self.particle_size_combobox.addItem(str(size))
        self.particle_size_combobox.setCurrentText("50")

        # Particle count
        self.particle_count_label = QLabel(language_wrapper.language_word_dict.get("particle_count"))
        retranslator.bind(self.particle_count_label, "particle_count", "")
        self.particle_count_combobox = QComboBox()
        for count in range(50, 10010, 10):
            self.particle_count_combobox.addItem(str(count))
        self.particle_count_combobox.setCurrentText("100")

        # Particle speed
        self.particle_speed_label = QLabel(language_wrapper.language_word_dict.get("particle_speed"))
        retranslator.bind(self.particle_speed_label, "particle_speed", "")
        self.particle_speed_combobox = QComboBox()
        for speed in range(3, 11):
            self.particle_speed_combobox.addItem(str(speed / 1000))

        # Start button
        self.start_button = QPushButton(language_wrapper.language_word_dict.get("particle_setting_ui_play"))
        retranslator.bind(self.start_button, "particle_setting_ui_play", "")
        self.start_button.clicked.connect(self.start_play_particle)

        # Checkboxes
        self.show_on_all_screen_checkbox = QCheckBox(language_wrapper.language_word_dict.get("Show on all screen"))
        retranslator.bind(self.show_on_all_screen_checkbox, "Show on all screen", "")
        self.show_on_all_screen_checkbox.clicked.connect(self.set_show_all_screen)

        # Target monitor selector
        self.target_monitor_label = QLabel(
            language_wrapper.language_word_dict.get("target_monitor_label", "Target monitor")
        )
        retranslator.bind(self.target_monitor_label, "target_monitor_label", "Target monitor")
        self.target_monitor_combobox = build_target_monitor_combobox()

        # Recent files
        self.recent_files_label = QLabel(language_wrapper.language_word_dict.get("recent_files_label", "Recent"))
        retranslator.bind(self.recent_files_label, "recent_files_label", "Recent")
        self.recent_files_combobox = build_recent_combobox("particle")
        self.recent_files_combobox.activated.connect(self._apply_recent_file)

        # Accept dropped image files
        self._drop_filter = enable_file_drop(
            self, (".png", ".jpg", ".jpeg", ".webp", ".bmp"), self._on_file_dropped
        )

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
        self.grid_layout.addWidget(self.target_monitor_label, 7, 0)
        self.grid_layout.addWidget(self.target_monitor_combobox, 7, 1)
        self.grid_layout.addWidget(self.recent_files_label, 8, 0)
        self.grid_layout.addWidget(self.recent_files_combobox, 8, 1)

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
            message_box.exec()
            return

        def factory(monitor):
            target = monitor or QGuiApplication.primaryScreen()
            geometry = target.availableGeometry()
            return self._create_particle_widget(geometry.width(), geometry.height())

        def present_on_monitor(widget: ParticleOpenGLWidget, monitor, _idx: int) -> None:
            widget.setScreen(monitor)
            widget.move(monitor.availableGeometry().topLeft())
            widget.showMaximized()

        dispatch_to_monitors(
            parent=self,
            show_all_screen=self.show_all_screen,
            factory=factory,
            present_primary=lambda widget: widget.showMaximized(),
            present_on_monitor=present_on_monitor,
            preferred_monitor_index=resolve_preferred_monitor(self.target_monitor_combobox),
        )

    def choose_and_copy_file_to_cwd_image_dir_then_play(self) -> None:
        front_engine_logger.info("[ParticleSettingUI] choose_and_copy_file_to_cwd_image_dir_then_play")
        self.ready_label.setText(language_wrapper.language_word_dict.get("Not Ready"))
        self.ready_to_play = False
        self.image_path = choose_image(self)
        if self.image_path:
            self.ready_label.setText(language_wrapper.language_word_dict.get("Ready"))
            self.ready_to_play = True
            add_recent_file("particle", self.image_path)
            reload_recent_combobox(self.recent_files_combobox, "particle")

    def _apply_recent_file(self, _index: int = 0) -> None:
        path = self.recent_files_combobox.currentData()
        self.recent_files_combobox.setCurrentIndex(0)
        if not path:
            return
        front_engine_logger.info(f"[ParticleSettingUI] _apply_recent_file | path={path}")
        self.image_path = path
        self.ready_to_play = True
        self.ready_label.setText(language_wrapper.language_word_dict.get("Ready"))

    def _on_file_dropped(self, path: str) -> None:
        front_engine_logger.info(f"[ParticleSettingUI] _on_file_dropped | path={path}")
        self.image_path = path
        self.ready_to_play = True
        self.ready_label.setText(language_wrapper.language_word_dict.get("Ready"))
        add_recent_file("particle", path)
        reload_recent_combobox(self.recent_files_combobox, "particle")

    def opacity_trick(self) -> None:
        front_engine_logger.info("[ParticleSettingUI] opacity_trick")
        self.opacity_slider_value_label.setText(str(self.opacity_slider.value()))

    def get_state(self) -> dict:
        return {
            "opacity": self.opacity_slider.value(),
            "image_path": self.image_path,
            "direction": self.choose_direction_combobox.currentText(),
            "size": self.particle_size_combobox.currentText(),
            "count": self.particle_count_combobox.currentText(),
            "speed": self.particle_speed_combobox.currentText(),
            "show_on_all_screen": self.show_on_all_screen_checkbox.isChecked(),
            "target_monitor": self.target_monitor_combobox.currentText(),
        }

    def set_state(self, state: dict) -> None:
        opacity = coerce_int(state.get("opacity"))
        if opacity is not None:
            self.opacity_slider.setValue(opacity)
        if state.get("image_path"):
            self.image_path = state["image_path"]
            self.ready_to_play = True
            self.ready_label.setText(language_wrapper.language_word_dict.get("Ready"))
        for combobox, key in (
            (self.choose_direction_combobox, "direction"),
            (self.particle_size_combobox, "size"),
            (self.particle_count_combobox, "count"),
            (self.particle_speed_combobox, "speed"),
        ):
            if state.get(key) is not None:
                index = combobox.findText(str(state[key]))
                if index >= 0:
                    combobox.setCurrentIndex(index)
        if "show_on_all_screen" in state:
            self.show_on_all_screen_checkbox.setChecked(bool(state["show_on_all_screen"]))
            self.show_all_screen = bool(state["show_on_all_screen"])
        if state.get("target_monitor") is not None:
            index = self.target_monitor_combobox.findText(str(state["target_monitor"]))
            if index >= 0:
                self.target_monitor_combobox.setCurrentIndex(index)