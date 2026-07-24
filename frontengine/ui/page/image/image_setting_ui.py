from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QGridLayout, QSlider, QLabel, QPushButton, QMessageBox, QCheckBox, QComboBox, QFileDialog,
)

from frontengine.show.image.paint_image import ImageWidget
from frontengine.ui.dialog.choose_file_dialog import choose_image
from frontengine.ui.page.utils import (
    build_recent_combobox,
    build_target_monitor_combobox,
    coerce_int,
    dispatch_to_monitors,
    enable_file_drop,
    list_media_files,
    reload_recent_combobox,
    resolve_preferred_monitor,
    show_on_primary_screen,
    show_on_selected_monitor,
)
from frontengine.user_setting.user_setting_file import add_recent_file
from frontengine.utils.logging.loggin_instance import front_engine_logger

# 輪播支援的圖片副檔名 / Image extensions the slideshow accepts
_SLIDESHOW_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class ImageSettingUI(QWidget):
    def __init__(self):
        front_engine_logger.info("[ImageSettingUI] Init")
        super().__init__()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # Init variable
        self.image_widget_list = []
        self.show_all_screen = False
        self.ready_to_play = False
        self.image_path: Optional[str] = None

        # Slideshow state
        self.slideshow_folder: Optional[str] = None
        self._slideshow_paths: list = []
        self._slideshow_index: int = 0
        self._slideshow_timer = QTimer(self)
        self._slideshow_timer.timeout.connect(self._advance_slideshow)

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

        # Start button
        self.start_button = QPushButton(language_wrapper.language_word_dict.get("image_setting_ui_play"))
        self.start_button.clicked.connect(self.start_play_image)

        # Checkboxes
        self.fullscreen_checkbox = QCheckBox(language_wrapper.language_word_dict.get("fullscreen_checkbox_label"))
        self.fullscreen_checkbox.setChecked(True)

        self.show_on_all_screen_checkbox = QCheckBox(language_wrapper.language_word_dict.get("Show on all screen"))
        self.show_on_all_screen_checkbox.clicked.connect(self.set_show_all_screen)

        self.show_on_bottom_checkbox = QCheckBox(language_wrapper.language_word_dict.get("Show on bottom"))

        # Target monitor selector
        self.target_monitor_label = QLabel(
            language_wrapper.language_word_dict.get("target_monitor_label", "Target monitor")
        )
        self.target_monitor_combobox = build_target_monitor_combobox()

        # Recent files
        self.recent_files_label = QLabel(language_wrapper.language_word_dict.get("recent_files_label", "Recent"))
        self.recent_files_combobox = build_recent_combobox("image")
        self.recent_files_combobox.activated.connect(self._apply_recent_file)

        # Slideshow controls
        self.slideshow_checkbox = QCheckBox(language_wrapper.language_word_dict.get("slideshow_label", "Slideshow"))
        self.slideshow_folder_button = QPushButton(
            language_wrapper.language_word_dict.get("slideshow_choose_folder", "Choose folder")
        )
        self.slideshow_folder_button.clicked.connect(self.choose_slideshow_folder)
        self.slideshow_interval_label = QLabel(
            language_wrapper.language_word_dict.get("slideshow_interval_label", "Interval (s)")
        )
        self.slideshow_interval_combobox = QComboBox()
        self.slideshow_interval_combobox.addItems(["3", "5", "10", "15", "30", "60"])
        self.slideshow_interval_combobox.setCurrentText("5")
        self.slideshow_shuffle_checkbox = QCheckBox(
            language_wrapper.language_word_dict.get("slideshow_shuffle", "Shuffle")
        )
        self.slideshow_recursive_checkbox = QCheckBox(
            language_wrapper.language_word_dict.get("slideshow_recursive", "Include subfolders")
        )

        # Accept dropped image files
        self._drop_filter = enable_file_drop(self, _SLIDESHOW_EXTENSIONS, self._on_file_dropped)

        # Layout
        self.grid_layout.addWidget(self.opacity_label, 0, 0)
        self.grid_layout.addWidget(self.opacity_slider_value_label, 0, 1)
        self.grid_layout.addWidget(self.opacity_slider, 0, 2)
        self.grid_layout.addWidget(self.choose_file_button, 1, 0)
        self.grid_layout.addWidget(self.ready_label, 1, 1)
        self.grid_layout.addWidget(self.fullscreen_checkbox, 1, 2)
        self.grid_layout.addWidget(self.start_button, 2, 0)
        self.grid_layout.addWidget(self.show_on_all_screen_checkbox, 2, 1)
        self.grid_layout.addWidget(self.show_on_bottom_checkbox, 2, 2)
        self.grid_layout.addWidget(self.target_monitor_label, 3, 0)
        self.grid_layout.addWidget(self.target_monitor_combobox, 3, 1)
        self.grid_layout.addWidget(self.recent_files_label, 4, 0)
        self.grid_layout.addWidget(self.recent_files_combobox, 4, 1)
        self.grid_layout.addWidget(self.slideshow_checkbox, 5, 0)
        self.grid_layout.addWidget(self.slideshow_folder_button, 5, 1)
        self.grid_layout.addWidget(self.slideshow_interval_label, 6, 0)
        self.grid_layout.addWidget(self.slideshow_interval_combobox, 6, 1)
        self.grid_layout.addWidget(self.slideshow_shuffle_checkbox, 7, 0)
        self.grid_layout.addWidget(self.slideshow_recursive_checkbox, 7, 1)

    def set_show_all_screen(self) -> None:
        front_engine_logger.info("[ImageSettingUI] set_show_all_screen")
        self.show_all_screen = self.show_on_all_screen_checkbox.isChecked()

    def _create_image_widget(self) -> ImageWidget:
        front_engine_logger.info("[ImageSettingUI] _create_image_widget")
        image_widget = ImageWidget(image_path=self.image_path)
        image_widget.set_ui_variable(opacity=float(self.opacity_slider.value()) / 100)
        image_widget.set_ui_window_flag(self.show_on_bottom_checkbox.isChecked())
        self.image_widget_list.append(image_widget)
        return image_widget

    def start_play_image(self) -> None:
        front_engine_logger.info("[ImageSettingUI] start_play_image")
        # In slideshow mode, prime the first image from the chosen folder.
        slideshow = self.slideshow_checkbox.isChecked() and self._prime_slideshow()
        if not self.image_path or not self.ready_to_play:
            message_box = QMessageBox(self)
            message_box.setText(language_wrapper.language_word_dict.get("not_prepare"))
            message_box.exec()
            return

        dispatch_to_monitors(
            parent=self,
            show_all_screen=self.show_all_screen,
            factory=lambda _monitor: self._create_image_widget(),
            present_primary=lambda widget: show_on_primary_screen(widget, self.fullscreen_checkbox),
            present_on_monitor=lambda widget, monitor, _idx: show_on_selected_monitor(
                widget, self.fullscreen_checkbox, monitor
            ),
            preferred_monitor_index=resolve_preferred_monitor(self.target_monitor_combobox),
        )
        if slideshow:
            self._slideshow_timer.start(self._slideshow_interval_ms())

    def choose_slideshow_folder(self) -> None:
        front_engine_logger.info("[ImageSettingUI] choose_slideshow_folder")
        folder = QFileDialog.getExistingDirectory(
            self, language_wrapper.language_word_dict.get("slideshow_choose_folder", "Choose folder")
        )
        if folder:
            self.slideshow_folder = folder

    def _slideshow_interval_ms(self) -> int:
        try:
            return max(1, int(self.slideshow_interval_combobox.currentText())) * 1000
        except (TypeError, ValueError):
            return 5000

    def _prime_slideshow(self) -> bool:
        """載入資料夾清單並以第一張圖作為起始 / Load the folder and prime the first image."""
        if not self.slideshow_folder:
            return False
        self._slideshow_paths = list_media_files(
            self.slideshow_folder,
            _SLIDESHOW_EXTENSIONS,
            recursive=self.slideshow_recursive_checkbox.isChecked(),
        )
        if not self._slideshow_paths:
            return False
        if self.slideshow_shuffle_checkbox.isChecked():
            # SystemRandom (os.urandom) avoids the insecure-PRNG warning; order
            # only needs to look random, so the cost is irrelevant.
            from random import SystemRandom

            SystemRandom().shuffle(self._slideshow_paths)
        self._slideshow_index = 0
        self.image_path = self._slideshow_paths[0]
        self.ready_to_play = True
        return True

    def _advance_slideshow(self) -> None:
        """輪播下一張，並清除已被關閉的覆蓋層 / Advance to the next image, pruning dead overlays."""
        if not self._slideshow_paths:
            self._slideshow_timer.stop()
            return
        self._slideshow_index = (self._slideshow_index + 1) % len(self._slideshow_paths)
        next_path = self._slideshow_paths[self._slideshow_index]
        for widget in list(self.image_widget_list):
            setter = getattr(widget, "set_image_path", None)
            if setter is None:
                continue
            try:
                setter(next_path)
            except RuntimeError:
                try:
                    self.image_widget_list.remove(widget)
                except ValueError:
                    pass
        if not self.image_widget_list:
            self._slideshow_timer.stop()

    def choose_and_copy_file_to_cwd_image_dir_then_play(self) -> None:
        front_engine_logger.info("[ImageSettingUI] choose_and_copy_file_to_cwd_image_dir_then_play")
        self.ready_label.setText(language_wrapper.language_word_dict.get("Not Ready"))
        self.ready_to_play = False
        self.image_path = choose_image(self)
        if self.image_path:
            self.ready_label.setText(language_wrapper.language_word_dict.get("Ready"))
            self.ready_to_play = True
            add_recent_file("image", self.image_path)
            reload_recent_combobox(self.recent_files_combobox, "image")

    def _apply_recent_file(self, _index: int = 0) -> None:
        path = self.recent_files_combobox.currentData()
        self.recent_files_combobox.setCurrentIndex(0)
        if not path:
            return
        front_engine_logger.info(f"[ImageSettingUI] _apply_recent_file | path={path}")
        self.image_path = path
        self.ready_to_play = True
        self.ready_label.setText(language_wrapper.language_word_dict.get("Ready"))

    def _on_file_dropped(self, path: str) -> None:
        front_engine_logger.info(f"[ImageSettingUI] _on_file_dropped | path={path}")
        self.image_path = path
        self.ready_to_play = True
        self.ready_label.setText(language_wrapper.language_word_dict.get("Ready"))
        add_recent_file("image", path)
        reload_recent_combobox(self.recent_files_combobox, "image")

    def opacity_trick(self) -> None:
        front_engine_logger.info("[ImageSettingUI] opacity_trick")
        self.opacity_slider_value_label.setText(str(self.opacity_slider.value()))

    def get_state(self) -> dict:
        return {
            "opacity": self.opacity_slider.value(),
            "image_path": self.image_path,
            "fullscreen": self.fullscreen_checkbox.isChecked(),
            "show_on_all_screen": self.show_on_all_screen_checkbox.isChecked(),
            "show_on_bottom": self.show_on_bottom_checkbox.isChecked(),
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
        if "fullscreen" in state:
            self.fullscreen_checkbox.setChecked(bool(state["fullscreen"]))
        if "show_on_all_screen" in state:
            self.show_on_all_screen_checkbox.setChecked(bool(state["show_on_all_screen"]))
            self.show_all_screen = bool(state["show_on_all_screen"])
        if "show_on_bottom" in state:
            self.show_on_bottom_checkbox.setChecked(bool(state["show_on_bottom"]))
        if state.get("target_monitor") is not None:
            index = self.target_monitor_combobox.findText(str(state["target_monitor"]))
            if index >= 0:
                self.target_monitor_combobox.setCurrentIndex(index)