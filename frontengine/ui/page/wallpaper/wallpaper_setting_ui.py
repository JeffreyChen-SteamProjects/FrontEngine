"""
桌布頁：把資料夾裡的圖片／動圖當桌布輪播，可隨機、可隨系統音量脈動，
而且每個螢幕可以指定不同的資料夾。

The wallpaper page: rotate a folder of images and animations beneath every
window, optionally shuffled and pulsing with the system audio level — and each
monitor can point at a different folder.
"""
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QGridLayout, QLabel, QPushButton, QSlider, QWidget,
)

from frontengine.show.wallpaper.wallpaper_widget import WallpaperWidget
from frontengine.ui.page.utils import coerce_int
from frontengine.utils.audio_meter.screen_audio import audio_level_provider_for_screen
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.playlist.playlist import Playlist, clamp_interval, collect_media


class WallpaperSettingUI(QWidget):
    """桌布設定頁 / The wallpaper settings page."""

    def __init__(self):
        front_engine_logger.info("[WallpaperSettingUI] Init")
        super().__init__()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        # 每個螢幕各自的資料夾、桌布與播放清單
        # Per-monitor folder, wallpaper widget and playlist.
        self.folders: Dict[int, str] = {}
        self.wallpaper_widgets: Dict[int, WallpaperWidget] = {}
        self.playlists: Dict[int, Playlist] = {}
        self.advance_timer = QTimer(self)
        self.advance_timer.timeout.connect(self.advance_all)

        # Monitor picker (per-monitor folders)
        self.monitor_label = QLabel(
            language_wrapper.language_word_dict.get("wallpaper_monitor_label", "Monitor"))
        self.monitor_combobox = QComboBox()
        for index, screen in enumerate(QGuiApplication.screens()):
            self.monitor_combobox.addItem(f"{index}: {screen.name()}", index)
        if self.monitor_combobox.count() == 0:
            self.monitor_combobox.addItem("0", 0)
        self.monitor_combobox.currentIndexChanged.connect(self._show_folder_for_monitor)
        self.folder_button = QPushButton(
            language_wrapper.language_word_dict.get("wallpaper_choose_folder", "Choose folder..."))
        self.folder_button.clicked.connect(self.choose_folder)
        self.folder_label = QLabel(
            language_wrapper.language_word_dict.get("wallpaper_no_folder", "No folder chosen"))
        self.folder_label.setWordWrap(True)

        # Playlist options
        self.interval_label = QLabel(
            language_wrapper.language_word_dict.get("wallpaper_interval_label", "Change every"))
        self.interval_combobox = QComboBox()
        for label, seconds in (("30s", 30), ("1m", 60), ("5m", 300), ("15m", 900), ("1h", 3600)):
            self.interval_combobox.addItem(label, seconds)
        self.interval_combobox.setCurrentText("5m")
        self.interval_combobox.currentIndexChanged.connect(self._apply_interval)
        self.shuffle_checkbox = QCheckBox(
            language_wrapper.language_word_dict.get("wallpaper_shuffle", "Shuffle"))
        self.recursive_checkbox = QCheckBox(
            language_wrapper.language_word_dict.get("wallpaper_recursive", "Include subfolders"))

        # Audio reaction
        self.react_checkbox = QCheckBox(
            language_wrapper.language_word_dict.get("wallpaper_audio_react", "React to audio"))
        self.react_checkbox.toggled.connect(self._apply_audio_react)
        self.react_strength_slider = QSlider(Qt.Orientation.Horizontal)
        self.react_strength_slider.setRange(0, 100)
        self.react_strength_slider.setValue(100)
        self.react_strength_slider.valueChanged.connect(self._apply_audio_react)

        # Start / stop
        self.start_button = QPushButton(
            language_wrapper.language_word_dict.get("wallpaper_start", "Start wallpaper"))
        self.start_button.clicked.connect(self.toggle_wallpaper)
        self.next_button = QPushButton(
            language_wrapper.language_word_dict.get("wallpaper_next", "Next wallpaper"))
        self.next_button.clicked.connect(self.advance_all)
        self.hint_label = QLabel(
            language_wrapper.language_word_dict.get(
                "wallpaper_hint",
                "Wallpapers sit beneath every window. Each monitor can use its own folder."))
        self.hint_label.setWordWrap(True)

        # Layout
        self.grid_layout.addWidget(self.monitor_label, 0, 0)
        self.grid_layout.addWidget(self.monitor_combobox, 0, 1)
        self.grid_layout.addWidget(self.folder_button, 0, 2)
        self.grid_layout.addWidget(self.folder_label, 1, 0, 1, 3)
        self.grid_layout.addWidget(self.interval_label, 2, 0)
        self.grid_layout.addWidget(self.interval_combobox, 2, 1)
        self.grid_layout.addWidget(self.shuffle_checkbox, 2, 2)
        self.grid_layout.addWidget(self.recursive_checkbox, 3, 0)
        self.grid_layout.addWidget(self.react_checkbox, 4, 0)
        self.grid_layout.addWidget(self.react_strength_slider, 4, 1, 1, 2)
        self.grid_layout.addWidget(self.start_button, 5, 0)
        self.grid_layout.addWidget(self.next_button, 5, 1)
        self.grid_layout.addWidget(self.hint_label, 6, 0, 1, 3)

    # --- folders ---------------------------------------------------------
    def current_monitor(self) -> int:
        data = self.monitor_combobox.currentData()
        return int(data) if data is not None else 0

    def choose_folder(self) -> None:
        """為目前選到的螢幕挑一個資料夾。"""
        folder = QFileDialog.getExistingDirectory(
            self, language_wrapper.language_word_dict.get(
                "wallpaper_choose_folder", "Choose folder..."))
        if folder:
            self.set_folder(self.current_monitor(), folder)

    def set_folder(self, monitor: int, folder: str) -> None:
        """指定某螢幕使用的資料夾。"""
        self.folders[int(monitor)] = str(folder)
        self._show_folder_for_monitor()

    def _show_folder_for_monitor(self) -> None:
        folder = self.folders.get(self.current_monitor())
        self.folder_label.setText(folder or language_wrapper.language_word_dict.get(
            "wallpaper_no_folder", "No folder chosen"))

    def build_playlist(self, monitor: int) -> Playlist:
        """依該螢幕的資料夾建立播放清單。"""
        items = collect_media(self.folders.get(int(monitor), ""),
                              recursive=self.recursive_checkbox.isChecked())
        return Playlist(items, shuffle=self.shuffle_checkbox.isChecked(),
                        interval_seconds=int(self.interval_combobox.currentData()))

    # --- lifecycle -------------------------------------------------------
    def toggle_wallpaper(self) -> None:
        if self.wallpaper_widgets:
            self.stop_wallpaper()
        else:
            self.start_wallpaper()

    def start_wallpaper(self) -> None:
        """為每個有指定資料夾的螢幕開一張桌布。"""
        front_engine_logger.info("[WallpaperSettingUI] start_wallpaper")
        self.stop_wallpaper()
        screens = QGuiApplication.screens()
        for monitor, folder in sorted(self.folders.items()):
            if not folder or monitor >= len(screens):
                continue
            playlist = self.build_playlist(monitor)
            if not len(playlist):
                front_engine_logger.warning(f"[WallpaperSettingUI] no media in {folder}")
                continue
            widget = WallpaperWidget(react_strength=self.react_strength_slider.value())
            widget.set_ui_window_flag(show_on_bottom=True)
            screen = screens[monitor]
            widget.setScreen(screen)
            widget.setGeometry(screen.geometry())
            widget.set_media(playlist.next())
            widget.set_audio_level_provider(audio_level_provider_for_screen(screen))
            widget.set_audio_react(self.react_checkbox.isChecked(),
                                   self.react_strength_slider.value())
            widget.show()
            widget.lower()
            self.wallpaper_widgets[monitor] = widget
            self.playlists[monitor] = playlist
        if self.wallpaper_widgets:
            self.advance_timer.start(
                clamp_interval(self.interval_combobox.currentData()) * 1000)
            self.start_button.setText(
                language_wrapper.language_word_dict.get("wallpaper_stop", "Stop wallpaper"))

    def stop_wallpaper(self) -> None:
        """收掉所有桌布。"""
        self.advance_timer.stop()
        for widget in list(self.wallpaper_widgets.values()):
            try:
                widget.close()
            except RuntimeError:
                pass
        self.wallpaper_widgets.clear()
        self.playlists.clear()
        self.start_button.setText(
            language_wrapper.language_word_dict.get("wallpaper_start", "Start wallpaper"))

    def advance_all(self) -> None:
        """每個螢幕各自換到清單的下一張。"""
        for monitor, widget in list(self.wallpaper_widgets.items()):
            playlist = self.playlists.get(monitor)
            if playlist is None:
                continue
            try:
                nxt = playlist.next()
                if nxt:
                    widget.set_media(nxt)
            except RuntimeError:
                self.wallpaper_widgets.pop(monitor, None)

    def _apply_interval(self) -> None:
        if self.advance_timer.isActive():
            self.advance_timer.start(
                clamp_interval(self.interval_combobox.currentData()) * 1000)

    def _apply_audio_react(self) -> None:
        for widget in list(self.wallpaper_widgets.values()):
            try:
                widget.set_audio_react(self.react_checkbox.isChecked(),
                                       self.react_strength_slider.value())
            except RuntimeError:
                pass

    # --- preset state ----------------------------------------------------
    def get_state(self) -> dict:
        return {
            "folders": {str(monitor): folder for monitor, folder in self.folders.items()},
            "interval": self.interval_combobox.currentText(),
            "shuffle": self.shuffle_checkbox.isChecked(),
            "recursive": self.recursive_checkbox.isChecked(),
            "audio_react": self.react_checkbox.isChecked(),
            "react_strength": self.react_strength_slider.value(),
        }

    def set_state(self, state: dict) -> None:
        folders = state.get("folders")
        if isinstance(folders, dict):
            self.folders = {}
            for monitor, folder in folders.items():
                try:
                    self.folders[int(monitor)] = str(folder)
                except (TypeError, ValueError):
                    continue
            self._show_folder_for_monitor()
        if state.get("interval") is not None:
            index = self.interval_combobox.findText(str(state["interval"]))
            if index >= 0:
                self.interval_combobox.setCurrentIndex(index)
        for checkbox, key in ((self.shuffle_checkbox, "shuffle"),
                              (self.recursive_checkbox, "recursive"),
                              (self.react_checkbox, "audio_react")):
            if key in state:
                checkbox.setChecked(bool(state[key]))
        strength = coerce_int(state.get("react_strength"))
        if strength is not None:
            self.react_strength_slider.setValue(strength)
