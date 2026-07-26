"""
桌布頁：把資料夾裡的圖片／動圖當桌布輪播，可隨機、可隨系統音量脈動，
而且每個螢幕可以指定不同的資料夾。

The wallpaper page: rotate a folder of images and animations beneath every
window, optionally shuffled and pulsing with the system audio level — and each
monitor can point at a different folder.
"""
from datetime import datetime
from typing import Callable, Dict

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QGridLayout, QLabel, QPushButton, QSlider, QSpinBox,
    QWidget,
)

from frontengine.show.wallpaper.wallpaper_widget import WallpaperWidget
from frontengine.ui.page.utils import (
    apply_checkbox_state, apply_combobox_text_state, apply_slider_state, apply_spinbox_state,
)
from frontengine.utils.audio_meter.screen_audio import audio_level_provider_for_screen
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import tr
# 多處共用的英文備援字串（只有在翻譯缺漏時才會看到）
# The English fallback shared by several call sites, seen only when a
# translation is missing.
_NO_FOLDER = "No folder chosen"

from frontengine.utils.playlist.playlist import (
    Playlist, ScheduledPlaylists, clamp_interval, collect_media,
)


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
        self.playlists: Dict[int, ScheduledPlaylists] = {}
        # 工作時段用的資料夾（可留空），以及判斷「現在幾點」的時鐘（測試可換掉）
        # The folder used during work hours (may be empty) and the clock that
        # decides what time it is - swappable in tests.
        self.quiet_folders: Dict[int, str] = {}
        self.now_provider: Callable[[], datetime] = datetime.now
        self.advance_timer = QTimer(self)
        self.advance_timer.timeout.connect(self.advance_all)

        # Monitor picker (per-monitor folders)
        self.monitor_label = tr(QLabel(), "wallpaper_monitor_label", "Monitor")
        self.monitor_combobox = QComboBox()
        for index, screen in enumerate(QGuiApplication.screens()):
            self.monitor_combobox.addItem(f"{index}: {screen.name()}", index)
        if self.monitor_combobox.count() == 0:
            self.monitor_combobox.addItem("0", 0)
        self.monitor_combobox.currentIndexChanged.connect(self._show_folder_for_monitor)
        self.folder_button = tr(QPushButton(), "wallpaper_choose_folder", "Choose folder...")
        self.folder_button.clicked.connect(self.choose_folder)
        self.folder_label = tr(QLabel(), "wallpaper_no_folder", _NO_FOLDER)
        self.folder_label.setWordWrap(True)

        # Playlist options
        self.interval_label = tr(QLabel(), "wallpaper_interval_label", "Change every")
        self.interval_combobox = QComboBox()
        for label, seconds in (("30s", 30), ("1m", 60), ("5m", 300), ("15m", 900), ("1h", 3600)):
            self.interval_combobox.addItem(label, seconds)
        self.interval_combobox.setCurrentText("5m")
        self.interval_combobox.currentIndexChanged.connect(self._apply_interval)
        self.shuffle_checkbox = tr(QCheckBox(), "wallpaper_shuffle", "Shuffle")
        self.recursive_checkbox = tr(QCheckBox(), "wallpaper_recursive", "Include subfolders")

        # Audio reaction
        self.react_checkbox = tr(QCheckBox(), "wallpaper_audio_react", "React to audio")
        self.react_checkbox.toggled.connect(self._apply_audio_react)
        self.react_strength_slider = QSlider(Qt.Orientation.Horizontal)
        self.react_strength_slider.setRange(0, 100)
        self.react_strength_slider.setValue(100)
        self.react_strength_slider.valueChanged.connect(self._apply_audio_react)

        # 工作時段：這段時間改播另一個資料夾（例如安靜、低干擾的桌布）
        # Work hours: play a different folder during this window - the quiet,
        # low-distraction set - and the usual one outside it.
        self.quiet_label = tr(QLabel(), "wallpaper_quiet_label", "Quiet hours")
        self.quiet_start_spinbox = QSpinBox()
        self.quiet_start_spinbox.setRange(0, 23)
        self.quiet_start_spinbox.setValue(9)
        self.quiet_end_spinbox = QSpinBox()
        self.quiet_end_spinbox.setRange(0, 23)
        self.quiet_end_spinbox.setValue(18)
        self.quiet_folder_button = tr(QPushButton(), "wallpaper_quiet_folder", "Quiet folder...")
        self.quiet_folder_button.clicked.connect(self.choose_quiet_folder)
        self.quiet_folder_label = tr(QLabel(), "wallpaper_no_folder", _NO_FOLDER)
        self.quiet_folder_label.setWordWrap(True)

        # Start / stop
        self.start_button = tr(QPushButton(), "wallpaper_start", "Start wallpaper")
        self.start_button.clicked.connect(self.toggle_wallpaper)
        self.next_button = tr(QPushButton(), "wallpaper_next", "Next wallpaper")
        self.next_button.clicked.connect(self.advance_all)
        self.hint_label = tr(QLabel(), "wallpaper_hint",
            "Wallpapers sit beneath every window. Each monitor can use its own folder.")
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
        self.grid_layout.addWidget(self.quiet_label, 5, 0)
        self.grid_layout.addWidget(self.quiet_start_spinbox, 5, 1)
        self.grid_layout.addWidget(self.quiet_end_spinbox, 5, 2)
        self.grid_layout.addWidget(self.quiet_folder_button, 6, 0)
        self.grid_layout.addWidget(self.quiet_folder_label, 6, 1, 1, 2)
        self.grid_layout.addWidget(self.start_button, 7, 0)
        self.grid_layout.addWidget(self.next_button, 7, 1)
        self.grid_layout.addWidget(self.hint_label, 8, 0, 1, 3)

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

    def choose_quiet_folder(self) -> None:
        """為目前選到的螢幕挑一個「工作時段」資料夾。"""
        folder = QFileDialog.getExistingDirectory(
            self, language_wrapper.language_word_dict.get(
                "wallpaper_quiet_folder", "Quiet folder..."))
        if folder:
            self.set_quiet_folder(self.current_monitor(), folder)

    def set_quiet_folder(self, monitor: int, folder: str) -> None:
        """指定某螢幕在工作時段使用的資料夾。"""
        self.quiet_folders[int(monitor)] = str(folder)
        self._show_folder_for_monitor()

    def _show_folder_for_monitor(self) -> None:
        empty = language_wrapper.language_word_dict.get(
            "wallpaper_no_folder", _NO_FOLDER)
        monitor = self.current_monitor()
        self.folder_label.setText(self.folders.get(monitor) or empty)
        self.quiet_folder_label.setText(self.quiet_folders.get(monitor) or empty)

    def build_playlist(self, monitor: int) -> Playlist:
        """依該螢幕的（一般時段）資料夾建立播放清單。"""
        return self._playlist_from(self.folders.get(int(monitor), ""))

    def _playlist_from(self, folder: str) -> Playlist:
        items = collect_media(folder or "", recursive=self.recursive_checkbox.isChecked())
        return Playlist(items, shuffle=self.shuffle_checkbox.isChecked(),
                        interval_seconds=int(self.interval_combobox.currentData()))

    def build_schedule(self, monitor: int) -> ScheduledPlaylists:
        """
        建立該螢幕的時段清單：工作時段用安靜資料夾，其餘時間用一般資料夾。
        沒設安靜資料夾（或裡面沒有媒體檔）就整天都用一般清單。
        The per-monitor schedule: the quiet folder during work hours, the usual
        one otherwise. With no quiet folder (or nothing in it) the normal
        playlist simply runs all day.
        """
        schedule = ScheduledPlaylists(default=self.build_playlist(monitor))
        quiet = self._playlist_from(self.quiet_folders.get(int(monitor), ""))
        if len(quiet):
            schedule.add_window(self.quiet_start_spinbox.value(),
                                self.quiet_end_spinbox.value(), quiet)
        return schedule

    def playlist_for_now(self, monitor: int) -> Playlist:
        """此刻該用的清單（依現在幾點決定）。"""
        schedule = self.playlists.get(int(monitor))
        if schedule is None:
            return self.build_playlist(monitor)
        return schedule.playlist_for(self.now_provider().hour) or schedule.default

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
            schedule = self.build_schedule(monitor)
            playlist = schedule.playlist_for(self.now_provider().hour) or schedule.default
            if playlist is None or not len(playlist):
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
            self.playlists[monitor] = schedule
        if self.wallpaper_widgets:
            self.advance_timer.start(
                clamp_interval(self.interval_combobox.currentData()) * 1000)
            self.start_button.setText(
                language_wrapper.language_word_dict.get("wallpaper_stop", "Stop wallpaper"))

    def stop_wallpaper(self) -> None:
        """收掉所有桌布。"""
        self.advance_timer.stop()
        for widget in tuple(self.wallpaper_widgets.values()):
            try:
                widget.close()
            except RuntimeError:
                pass
        self.wallpaper_widgets.clear()
        self.playlists.clear()
        self.start_button.setText(
            language_wrapper.language_word_dict.get("wallpaper_start", "Start wallpaper"))

    def advance_all(self) -> None:
        """每個螢幕各自換到「此刻該用的清單」的下一張。"""
        for monitor, widget in tuple(self.wallpaper_widgets.items()):
            playlist = self.playlist_for_now(monitor)
            if playlist is None or not len(playlist):
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
        for widget in tuple(self.wallpaper_widgets.values()):
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
            "quiet_folders": {str(monitor): folder
                              for monitor, folder in self.quiet_folders.items()},
            "quiet_start": self.quiet_start_spinbox.value(),
            "quiet_end": self.quiet_end_spinbox.value(),
        }

    def set_state(self, state: dict) -> None:
        """把預設集的內容還原到這一頁的控制項上。"""
        for attribute in ("folders", "quiet_folders"):
            folders = state.get(attribute)
            if isinstance(folders, dict):
                setattr(self, attribute, _monitor_folders(folders))
        self._show_folder_for_monitor()
        apply_spinbox_state(state, ((self.quiet_start_spinbox, "quiet_start"),
                                    (self.quiet_end_spinbox, "quiet_end")))
        apply_slider_state(state, ((self.react_strength_slider, "react_strength"),))
        apply_combobox_text_state(state, ((self.interval_combobox, "interval"),))
        apply_checkbox_state(state, ((self.shuffle_checkbox, "shuffle"),
                                     (self.recursive_checkbox, "recursive"),
                                     (self.react_checkbox, "audio_react")))


def _monitor_folders(folders: dict) -> Dict[int, str]:
    """
    把儲存的 {螢幕編號: 資料夾} 整理回來；編號不是數字的項目直接跳過，
    不讓一筆手改壞的資料毀掉整份設定。
    Restore the saved {monitor: folder} map, skipping entries whose key is not a
    number so one hand-edited line cannot spoil the rest.
    """
    restored: Dict[int, str] = {}
    for monitor, folder in folders.items():
        try:
            restored[int(monitor)] = str(folder)
        except (TypeError, ValueError):
            continue
    return restored
