"""
桌面小工具分頁：音訊頻譜、正在播放、系統監控折線圖、便利貼。

**頻譜要注意**：它和寵物／桌布的律動不同，必須真的擷取系統輸出的音訊才能算
頻率。樣本只在記憶體裡做 FFT，不寫檔也不外傳，關掉就停止擷取；頁面上也寫了
這件事，不讓使用者在不知情的狀況下開著。

The desktop widgets page: audio spectrum, now playing, a system monitor
sparkline, and sticky notes.

**Note on the spectrum**: unlike the meter-only pet and wallpaper reactions, it
has to capture the system output stream to compute frequencies. Samples are
FFT'd in memory, never stored or sent, and capture stops with the overlay - and
the page says so, so nobody runs it unaware.
"""
from typing import Dict, List

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QGridLayout, QLabel, QPushButton, QSpinBox, QWidget,
)

from frontengine.show.monitor.monitor_widget import NowPlayingWidget, SystemMonitorWidget
from frontengine.show.notes.sticky_note_widget import StickyNoteWidget, note_state, restore_notes
from frontengine.show.spectrum.spectrum_widget import STYLE_BARS, STYLE_RING, SpectrumWidget
from frontengine.ui.page.utils import coerce_int
from frontengine.utils.audio_meter.loopback_capture import LoopbackSpectrum, available
from frontengine.utils.audio_meter.spectrum_analyzer import DEFAULT_BANDS
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import tr
from frontengine.utils.now_playing.now_playing import now_playing
from frontengine.user_setting.user_setting_file import user_setting_dict, write_user_setting


def _t(key: str, fallback: str) -> str:
    return language_wrapper.language_word_dict.get(key, fallback)


class WidgetsSettingUI(QWidget):
    """桌面小工具設定頁 / The desktop widgets page."""

    def __init__(self):
        front_engine_logger.info("[WidgetsSettingUI] Init")
        super().__init__()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        self.spectrum_widget_list: List[SpectrumWidget] = []
        self.monitor_widget_list: List[SystemMonitorWidget] = []
        self.now_playing_widget_list: List[NowPlayingWidget] = []
        self.note_widget_list: List[StickyNoteWidget] = []
        self.capture = LoopbackSpectrum(DEFAULT_BANDS)

        self._build_spectrum_row()
        self._build_monitor_row()
        self._build_note_row()
        self.hint_label = tr(QLabel(), "widgets_hint",
            "The spectrum captures the audio your speakers are playing so it can "
            "compute frequencies. It is analysed in memory only - nothing is recorded "
            "or sent - and capture stops when you stop the spectrum.")
        self.hint_label.setWordWrap(True)

        self.grid_layout.addWidget(self.spectrum_label, 0, 0)
        self.grid_layout.addWidget(self.spectrum_style_combobox, 0, 1)
        self.grid_layout.addWidget(self.spectrum_button, 0, 2)
        self.grid_layout.addWidget(self.spectrum_bands_label, 1, 0)
        self.grid_layout.addWidget(self.spectrum_bands_spinbox, 1, 1)
        self.grid_layout.addWidget(self.monitor_label, 2, 0)
        self.grid_layout.addWidget(self.monitor_history_spinbox, 2, 1)
        self.grid_layout.addWidget(self.monitor_button, 2, 2)
        self.grid_layout.addWidget(self.now_playing_button, 3, 0)
        self.grid_layout.addWidget(self.note_label, 4, 0)
        self.grid_layout.addWidget(self.note_button, 4, 1)
        self.grid_layout.addWidget(self.note_close_button, 4, 2)
        self.grid_layout.addWidget(self.note_restore_checkbox, 5, 0, 1, 3)
        self.grid_layout.addWidget(self.hint_label, 6, 0, 1, 3)

    # --- construction helpers -------------------------------------------
    def _build_spectrum_row(self) -> None:
        self.spectrum_label = tr(QLabel(), "widgets_spectrum_label", "Audio spectrum")
        self.spectrum_style_combobox = QComboBox()
        self.spectrum_style_combobox.addItem(_t("widgets_spectrum_bars", "Bars"), STYLE_BARS)
        self.spectrum_style_combobox.addItem(_t("widgets_spectrum_ring", "Ring"), STYLE_RING)
        self.spectrum_style_combobox.currentIndexChanged.connect(self._apply_spectrum_settings)
        self.spectrum_bands_label = tr(QLabel(), "widgets_spectrum_bands", "Bands")
        self.spectrum_bands_spinbox = QSpinBox()
        self.spectrum_bands_spinbox.setRange(4, 64)
        self.spectrum_bands_spinbox.setValue(DEFAULT_BANDS)
        self.spectrum_bands_spinbox.valueChanged.connect(self._apply_spectrum_settings)
        self.spectrum_button = tr(QPushButton(), "widgets_spectrum_start", "Start spectrum")
        self.spectrum_button.clicked.connect(self.toggle_spectrum)
        if not available():
            self.spectrum_button.setEnabled(False)
            self.spectrum_button.setToolTip(
                _t("widgets_spectrum_unavailable", "Audio capture is Windows only."))

    def _build_monitor_row(self) -> None:
        self.monitor_label = tr(QLabel(), "widgets_monitor_label", "System monitor")
        self.monitor_history_spinbox = QSpinBox()
        self.monitor_history_spinbox.setRange(10, 300)
        self.monitor_history_spinbox.setValue(60)
        self.monitor_history_spinbox.valueChanged.connect(self._apply_monitor_settings)
        self.monitor_button = tr(QPushButton(), "widgets_monitor_start", "Start monitor")
        self.monitor_button.clicked.connect(self.toggle_monitor)
        self.now_playing_button = tr(QPushButton(), "widgets_now_playing_start",
            "Show now playing")
        self.now_playing_button.clicked.connect(self.toggle_now_playing)

    def _build_note_row(self) -> None:
        self.note_label = tr(QLabel(), "widgets_note_label", "Sticky note")
        self.note_button = tr(QPushButton(), "widgets_note_add", "New note")
        self.note_button.clicked.connect(self.add_note)
        self.note_close_button = tr(QPushButton(), "widgets_note_close", "Close notes")
        self.note_close_button.clicked.connect(self.close_notes)
        self.note_restore_checkbox = tr(QCheckBox(), "widgets_note_restore",
            "Reopen my notes when FrontEngine starts")
        self.note_restore_checkbox.setChecked(bool(user_setting_dict.get("sticky_notes_restore")))
        self.note_restore_checkbox.toggled.connect(self._store_note_restore)

    # --- spectrum --------------------------------------------------------
    def toggle_spectrum(self) -> None:
        if self.spectrum_widget_list:
            self.stop_spectrum()
        else:
            self.start_spectrum()

    def start_spectrum(self) -> None:
        """開一個頻譜覆蓋層，並開始擷取（擷取只在這段期間進行）。"""
        front_engine_logger.info("[WidgetsSettingUI] start_spectrum")
        if not self.capture.start():
            front_engine_logger.warning("[WidgetsSettingUI] loopback capture unavailable")
            return
        self.capture.set_bands(self.spectrum_bands_spinbox.value())
        widget = SpectrumWidget(self.spectrum_bands_spinbox.value(),
                                self.spectrum_style_combobox.currentData())
        widget.set_level_provider(self.capture.bands)
        widget.set_ui_window_flag(show_on_bottom=False)
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            widget.setGeometry(area.x() + area.width() // 4, area.y() + area.height() * 2 // 3,
                               area.width() // 2, area.height() // 5)
        widget.show()
        widget.start()
        self.spectrum_widget_list.append(widget)
        self.spectrum_button.setText(_t("widgets_spectrum_stop", "Stop spectrum"))

    def stop_spectrum(self) -> None:
        """收掉頻譜並停止擷取。"""
        self.capture.stop()
        for widget in self.spectrum_widget_list[:]:
            try:
                widget.close()
            except RuntimeError:
                pass
        self.spectrum_widget_list.clear()
        self.spectrum_button.setText(_t("widgets_spectrum_start", "Start spectrum"))

    def _apply_spectrum_settings(self) -> None:
        bands = self.spectrum_bands_spinbox.value()
        self.capture.set_bands(bands)
        for widget in self.spectrum_widget_list[:]:
            try:
                widget.set_bands(bands)
                widget.set_style(self.spectrum_style_combobox.currentData())
            except RuntimeError:
                self.spectrum_widget_list.remove(widget)

    # --- system monitor --------------------------------------------------
    def toggle_monitor(self) -> None:
        if self.monitor_widget_list:
            self.stop_monitor()
        else:
            self.start_monitor()

    def start_monitor(self) -> None:
        front_engine_logger.info("[WidgetsSettingUI] start_monitor")
        widget = SystemMonitorWidget(self.monitor_history_spinbox.value())
        widget.set_ui_window_flag(show_on_bottom=False)
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            widget.move(area.x() + area.width() - widget.width() - 40, area.y() + 40)
        widget.show()
        widget.start()
        self.monitor_widget_list.append(widget)
        self.monitor_button.setText(_t("widgets_monitor_stop", "Stop monitor"))

    def stop_monitor(self) -> None:
        for widget in self.monitor_widget_list[:]:
            try:
                widget.close()
            except RuntimeError:
                pass
        self.monitor_widget_list.clear()
        self.monitor_button.setText(_t("widgets_monitor_start", "Start monitor"))

    def _apply_monitor_settings(self) -> None:
        for widget in self.monitor_widget_list[:]:
            try:
                widget.set_history(self.monitor_history_spinbox.value())
            except RuntimeError:
                self.monitor_widget_list.remove(widget)

    # --- now playing -----------------------------------------------------
    def toggle_now_playing(self) -> None:
        if self.now_playing_widget_list:
            self.stop_now_playing()
        else:
            self.start_now_playing()

    def start_now_playing(self) -> None:
        front_engine_logger.info("[WidgetsSettingUI] start_now_playing")
        widget = NowPlayingWidget(now_playing)
        widget.set_ui_window_flag(show_on_bottom=False)
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            widget.move(area.x() + 40, area.y() + area.height() - widget.height() - 80)
        widget.show()
        widget.start()
        self.now_playing_widget_list.append(widget)
        self.now_playing_button.setText(_t("widgets_now_playing_stop", "Hide now playing"))

    def stop_now_playing(self) -> None:
        for widget in self.now_playing_widget_list[:]:
            try:
                widget.close()
            except RuntimeError:
                pass
        self.now_playing_widget_list.clear()
        self.now_playing_button.setText(_t("widgets_now_playing_start", "Show now playing"))

    # --- sticky notes ----------------------------------------------------
    def add_note(self, text: str = "") -> StickyNoteWidget:
        """開一張新的便利貼。"""
        front_engine_logger.info("[WidgetsSettingUI] add_note")
        note = StickyNoteWidget(text)
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            offset = 30 * len(self.note_widget_list)
            note.move(area.x() + 120 + offset, area.y() + 120 + offset)
        note.show()
        self.note_widget_list.append(note)
        return note

    def close_notes(self) -> None:
        """收掉所有便利貼（收之前先把內容存起來）。"""
        self.save_notes()
        for note in self.note_widget_list[:]:
            try:
                note.close()
            except RuntimeError:
                pass
        self.note_widget_list.clear()

    def save_notes(self) -> List[Dict]:
        """把目前的便利貼內容與位置寫進設定。"""
        states = []
        for note in self.note_widget_list[:]:
            try:
                states.append(note_state(note))
            except RuntimeError:
                self.note_widget_list.remove(note)
        user_setting_dict["sticky_notes"] = states
        write_user_setting()
        return states

    def restore_saved_notes(self) -> List[StickyNoteWidget]:
        """把上次的便利貼開回來（只有在使用者選擇要還原時才會被呼叫）。"""
        notes = restore_notes(user_setting_dict.get("sticky_notes"), self.note_widget_list)
        for note in notes:
            note.show()
        return notes

    def _store_note_restore(self, enabled: bool) -> None:
        user_setting_dict["sticky_notes_restore"] = bool(enabled)
        write_user_setting()

    # --- preset state ----------------------------------------------------
    def get_state(self) -> dict:
        return {
            "spectrum_style": self.spectrum_style_combobox.currentData(),
            "spectrum_bands": self.spectrum_bands_spinbox.value(),
            "monitor_history": self.monitor_history_spinbox.value(),
            "notes_restore": self.note_restore_checkbox.isChecked(),
        }

    def set_state(self, state: dict) -> None:
        style = state.get("spectrum_style")
        if style is not None:
            index = self.spectrum_style_combobox.findData(str(style))
            if index >= 0:
                self.spectrum_style_combobox.setCurrentIndex(index)
        for spinbox, key in ((self.spectrum_bands_spinbox, "spectrum_bands"),
                             (self.monitor_history_spinbox, "monitor_history")):
            value = coerce_int(state.get(key))
            if value is not None:
                spinbox.setValue(max(spinbox.minimum(), min(spinbox.maximum(), value)))
        if "notes_restore" in state:
            self.note_restore_checkbox.setChecked(bool(state["notes_restore"]))
