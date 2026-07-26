"""
直播與遊戲分頁：準星、提詞機、音效板、OBS 控制。

準星只是疊在畫面上的一層——不注入遊戲、不讀記憶體、不改任何遊戲檔案。
OBS 控制走它自己內建的 WebSocket，密碼只留在本機設定裡。

The stream and gaming page: crosshair, teleprompter, soundboard, OBS control.

The crosshair is only a layer on top - nothing injected, no memory read, no
game file touched. OBS control uses its own built-in WebSocket, and the
password stays in the local settings.
"""
from typing import List, Optional

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QGridLayout, QLabel, QLineEdit, QListWidget, QPlainTextEdit,
    QPushButton, QSpinBox, QWidget,
)

from frontengine.show.gaming.crosshair_widget import (
    DEFAULT_COLOR, DEFAULT_GAP, DEFAULT_SIZE, DEFAULT_THICKNESS, STYLE_CIRCLE, STYLE_CROSS,
    STYLE_DOT, STYLE_T_SHAPE, CrosshairWidget,
)
from frontengine.show.teleprompter.teleprompter_widget import (
    DEFAULT_FONT_SIZE, DEFAULT_SPEED, MAX_FONT_SIZE, MAX_SPEED, MIN_FONT_SIZE, MIN_SPEED,
    TeleprompterWidget,
)
from frontengine.ui.page.utils import coerce_int
from frontengine.user_setting.user_setting_file import user_setting_dict, write_user_setting
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.obs.obs_client import ObsClient
from frontengine.utils.obs.obs_protocol import DEFAULT_HOST, DEFAULT_PORT
from frontengine.utils.soundboard.soundboard import Soundboard


def _t(key: str, fallback: str) -> str:
    return language_wrapper.language_word_dict.get(key, fallback)


class StreamSettingUI(QWidget):
    """直播與遊戲設定頁 / The stream and gaming page."""

    def __init__(self):
        front_engine_logger.info("[StreamSettingUI] Init")
        super().__init__()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        self.crosshair_widget_list: List[CrosshairWidget] = []
        self.teleprompter_widget_list: List[TeleprompterWidget] = []
        self.soundboard = Soundboard(self)
        self.soundboard.load(user_setting_dict.get("soundboard"))
        self.last_obs_result: Optional[tuple] = None

        self._build_crosshair_row()
        self._build_teleprompter_row()
        self._build_soundboard_row()
        self._build_obs_row()
        self.hint_label = QLabel(
            _t("stream_hint",
               "The crosshair is only drawn on top - no game is modified. OBS control uses "
               "its own WebSocket; the password is kept in your local settings."))
        self.hint_label.setWordWrap(True)

        self.grid_layout.addWidget(self.crosshair_label, 0, 0)
        self.grid_layout.addWidget(self.crosshair_style_combobox, 0, 1)
        self.grid_layout.addWidget(self.crosshair_button, 0, 2)
        self.grid_layout.addWidget(self.crosshair_size_spinbox, 1, 1)
        self.grid_layout.addWidget(self.crosshair_color_edit, 1, 2)
        self.grid_layout.addWidget(self.teleprompter_label, 2, 0)
        self.grid_layout.addWidget(self.teleprompter_speed_spinbox, 2, 1)
        self.grid_layout.addWidget(self.teleprompter_button, 2, 2)
        self.grid_layout.addWidget(self.teleprompter_edit, 3, 0, 1, 3)
        self.grid_layout.addWidget(self.teleprompter_font_spinbox, 4, 1)
        self.grid_layout.addWidget(self.teleprompter_mirror_checkbox, 4, 2)
        self.grid_layout.addWidget(self.sound_label, 5, 0)
        self.grid_layout.addWidget(self.sound_add_button, 5, 1)
        self.grid_layout.addWidget(self.sound_remove_button, 5, 2)
        self.grid_layout.addWidget(self.sound_list, 6, 0, 1, 2)
        self.grid_layout.addWidget(self.sound_play_button, 6, 2)
        self.grid_layout.addWidget(self.obs_label, 7, 0)
        self.grid_layout.addWidget(self.obs_host_edit, 7, 1)
        self.grid_layout.addWidget(self.obs_port_spinbox, 7, 2)
        self.grid_layout.addWidget(self.obs_password_edit, 8, 1)
        self.grid_layout.addWidget(self.obs_scene_edit, 8, 2)
        self.grid_layout.addWidget(self.obs_scene_button, 9, 0)
        self.grid_layout.addWidget(self.obs_record_button, 9, 1)
        self.grid_layout.addWidget(self.obs_stream_button, 9, 2)
        self.grid_layout.addWidget(self.hint_label, 10, 0, 1, 3)
        self.reload_sounds()

    # --- construction ----------------------------------------------------
    def _build_crosshair_row(self) -> None:
        self.crosshair_label = QLabel(_t("stream_crosshair_label", "Crosshair"))
        self.crosshair_style_combobox = QComboBox()
        for style, key, fallback in ((STYLE_CROSS, "stream_crosshair_cross", "Cross"),
                                     (STYLE_DOT, "stream_crosshair_dot", "Dot"),
                                     (STYLE_CIRCLE, "stream_crosshair_circle", "Circle"),
                                     (STYLE_T_SHAPE, "stream_crosshair_t", "T shape")):
            self.crosshair_style_combobox.addItem(_t(key, fallback), style)
        self.crosshair_style_combobox.currentIndexChanged.connect(self._apply_crosshair)
        self.crosshair_size_spinbox = QSpinBox()
        self.crosshair_size_spinbox.setRange(4, 200)
        self.crosshair_size_spinbox.setValue(DEFAULT_SIZE)
        self.crosshair_size_spinbox.valueChanged.connect(self._apply_crosshair)
        self.crosshair_color_edit = QLineEdit(DEFAULT_COLOR)
        self.crosshair_color_edit.editingFinished.connect(self._apply_crosshair)
        self.crosshair_button = QPushButton(_t("stream_crosshair_start", "Show crosshair"))
        self.crosshair_button.clicked.connect(self.toggle_crosshair)

    def _build_teleprompter_row(self) -> None:
        self.teleprompter_label = QLabel(_t("stream_teleprompter_label", "Teleprompter"))
        self.teleprompter_edit = QPlainTextEdit()
        self.teleprompter_edit.setPlaceholderText(
            _t("stream_teleprompter_script", "Paste your script here"))
        self.teleprompter_speed_spinbox = QSpinBox()
        self.teleprompter_speed_spinbox.setRange(MIN_SPEED, MAX_SPEED)
        self.teleprompter_speed_spinbox.setValue(DEFAULT_SPEED)
        self.teleprompter_speed_spinbox.valueChanged.connect(self._apply_teleprompter)
        self.teleprompter_font_spinbox = QSpinBox()
        self.teleprompter_font_spinbox.setRange(MIN_FONT_SIZE, MAX_FONT_SIZE)
        self.teleprompter_font_spinbox.setValue(DEFAULT_FONT_SIZE)
        self.teleprompter_font_spinbox.valueChanged.connect(self._apply_teleprompter)
        self.teleprompter_mirror_checkbox = QCheckBox(_t("stream_teleprompter_mirror", "Mirror"))
        self.teleprompter_mirror_checkbox.toggled.connect(self._apply_teleprompter)
        self.teleprompter_button = QPushButton(_t("stream_teleprompter_start", "Start prompter"))
        self.teleprompter_button.clicked.connect(self.toggle_teleprompter)

    def _build_soundboard_row(self) -> None:
        self.sound_label = QLabel(_t("stream_sound_label", "Soundboard"))
        self.sound_list = QListWidget()
        self.sound_list.itemDoubleClicked.connect(lambda _item: self.play_selected_sound())
        self.sound_add_button = QPushButton(_t("stream_sound_add", "Add sound"))
        self.sound_add_button.clicked.connect(self.add_sound)
        self.sound_remove_button = QPushButton(_t("stream_sound_remove", "Remove"))
        self.sound_remove_button.clicked.connect(self.remove_selected_sound)
        self.sound_play_button = QPushButton(_t("stream_sound_play", "Play"))
        self.sound_play_button.clicked.connect(self.play_selected_sound)

    def _build_obs_row(self) -> None:
        settings = user_setting_dict.get("obs", {})
        settings = settings if isinstance(settings, dict) else {}
        self.obs_label = QLabel(_t("stream_obs_label", "OBS"))
        self.obs_host_edit = QLineEdit(str(settings.get("host", DEFAULT_HOST)))
        self.obs_port_spinbox = QSpinBox()
        self.obs_port_spinbox.setRange(1, 65535)
        self.obs_port_spinbox.setValue(coerce_int(settings.get("port")) or DEFAULT_PORT)
        self.obs_password_edit = QLineEdit(str(settings.get("password", "")))
        self.obs_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.obs_password_edit.setPlaceholderText(_t("stream_obs_password", "WebSocket password"))
        self.obs_scene_edit = QLineEdit(str(settings.get("scene", "")))
        self.obs_scene_edit.setPlaceholderText(_t("stream_obs_scene", "Scene name"))
        self.obs_scene_button = QPushButton(_t("stream_obs_switch", "Switch scene"))
        self.obs_scene_button.clicked.connect(self.switch_obs_scene)
        self.obs_record_button = QPushButton(_t("stream_obs_record", "Toggle recording"))
        self.obs_record_button.clicked.connect(lambda: self.toggle_obs("record"))
        self.obs_stream_button = QPushButton(_t("stream_obs_stream", "Toggle streaming"))
        self.obs_stream_button.clicked.connect(lambda: self.toggle_obs("stream"))
        self._obs_recording = False
        self._obs_streaming = False

    # --- crosshair -------------------------------------------------------
    def toggle_crosshair(self) -> None:
        if self.crosshair_widget_list:
            self.stop_crosshair()
        else:
            self.start_crosshair()

    def start_crosshair(self) -> None:
        front_engine_logger.info("[StreamSettingUI] start_crosshair")
        widget = CrosshairWidget(self.crosshair_style_combobox.currentData(),
                                 self.crosshair_color_edit.text(),
                                 self.crosshair_size_spinbox.value(),
                                 DEFAULT_THICKNESS, DEFAULT_GAP)
        widget.set_ui_window_flag(show_on_bottom=False)
        widget.centre_on_screen(QGuiApplication.primaryScreen())
        widget.show()
        self.crosshair_widget_list.append(widget)
        self.crosshair_button.setText(_t("stream_crosshair_stop", "Hide crosshair"))

    def stop_crosshair(self) -> None:
        for widget in list(self.crosshair_widget_list):
            try:
                widget.close()
            except RuntimeError:
                pass
        self.crosshair_widget_list.clear()
        self.crosshair_button.setText(_t("stream_crosshair_start", "Show crosshair"))

    def _apply_crosshair(self) -> None:
        for widget in list(self.crosshair_widget_list):
            try:
                widget.set_crosshair(style=self.crosshair_style_combobox.currentData(),
                                     color=self.crosshair_color_edit.text(),
                                     size=self.crosshair_size_spinbox.value())
            except RuntimeError:
                self.crosshair_widget_list.remove(widget)

    # --- teleprompter ----------------------------------------------------
    def toggle_teleprompter(self) -> None:
        if self.teleprompter_widget_list:
            self.stop_teleprompter()
        else:
            self.start_teleprompter()

    def start_teleprompter(self) -> None:
        front_engine_logger.info("[StreamSettingUI] start_teleprompter")
        widget = TeleprompterWidget(self.teleprompter_edit.toPlainText(),
                                    self.teleprompter_speed_spinbox.value(),
                                    self.teleprompter_font_spinbox.value(),
                                    self.teleprompter_mirror_checkbox.isChecked())
        widget.set_ui_window_flag(show_on_bottom=False)
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            widget.setGeometry(area.x() + area.width() // 6, area.y() + area.height() // 6,
                               area.width() * 2 // 3, area.height() // 2)
        widget.show()
        widget.start()
        self.teleprompter_widget_list.append(widget)
        self.teleprompter_button.setText(_t("stream_teleprompter_stop", "Stop prompter"))

    def stop_teleprompter(self) -> None:
        for widget in list(self.teleprompter_widget_list):
            try:
                widget.close()
            except RuntimeError:
                pass
        self.teleprompter_widget_list.clear()
        self.teleprompter_button.setText(_t("stream_teleprompter_start", "Start prompter"))

    def _apply_teleprompter(self) -> None:
        for widget in list(self.teleprompter_widget_list):
            try:
                widget.set_speed(self.teleprompter_speed_spinbox.value())
                widget.set_font_size(self.teleprompter_font_spinbox.value())
                widget.set_mirrored(self.teleprompter_mirror_checkbox.isChecked())
            except RuntimeError:
                self.teleprompter_widget_list.remove(widget)

    # --- soundboard ------------------------------------------------------
    def reload_sounds(self) -> int:
        """重畫音效清單，回傳數量。"""
        self.sound_list.clear()
        for slot in self.soundboard.slots:
            suffix = f"  [{slot['hotkey']}]" if slot["hotkey"] else ""
            self.sound_list.addItem(f"{slot['label']}{suffix}")
        return self.sound_list.count()

    def add_sound(self, path: str = "") -> bool:
        """加一個音效（沒給路徑就開檔案選擇器）。"""
        chosen = str(path) if path else QFileDialog.getOpenFileName(
            self, _t("stream_sound_add", "Add sound"), "",
            "Sound (*.wav *.mp3 *.ogg *.m4a *.flac)")[0]
        if not chosen:
            return False
        if self.soundboard.add(chosen) is None:
            return False
        self.save_sounds()
        self.reload_sounds()
        return True

    def remove_selected_sound(self) -> bool:
        row = self.sound_list.currentRow()
        if not self.soundboard.remove(row):
            return False
        self.save_sounds()
        self.reload_sounds()
        return True

    def play_selected_sound(self) -> bool:
        return self.soundboard.play(self.sound_list.currentRow())

    def save_sounds(self) -> None:
        user_setting_dict["soundboard"] = self.soundboard.to_list()
        write_user_setting()

    # --- OBS -------------------------------------------------------------
    def obs_client(self) -> ObsClient:
        """依目前欄位建立一個 OBS 連線物件（順手記住設定）。"""
        self.save_obs_settings()
        return ObsClient(self.obs_host_edit.text(), self.obs_port_spinbox.value(),
                         self.obs_password_edit.text())

    def save_obs_settings(self) -> None:
        user_setting_dict["obs"] = {
            "host": self.obs_host_edit.text().strip() or DEFAULT_HOST,
            "port": self.obs_port_spinbox.value(),
            "password": self.obs_password_edit.text(),
            "scene": self.obs_scene_edit.text().strip(),
        }
        write_user_setting()

    def switch_obs_scene(self) -> bool:
        """切換到欄位裡填的場景；沒填就什麼都不做。"""
        scene = self.obs_scene_edit.text().strip()
        if not scene:
            return False
        client = self.obs_client()
        client.finished.connect(self._remember_obs_result)
        client.switch_scene(scene)
        return True

    def toggle_obs(self, what: str) -> bool:
        """切換 OBS 的錄影或直播狀態。"""
        client = self.obs_client()
        client.finished.connect(self._remember_obs_result)
        if what == "record":
            self._obs_recording = not self._obs_recording
            client.set_recording(self._obs_recording)
        else:
            self._obs_streaming = not self._obs_streaming
            client.set_streaming(self._obs_streaming)
        return True

    def _remember_obs_result(self, ok: bool, detail: str) -> None:
        self.last_obs_result = (bool(ok), str(detail))
        front_engine_logger.info(f"[StreamSettingUI] obs result | ok={ok} {detail}")

    # --- preset state ----------------------------------------------------
    def get_state(self) -> dict:
        return {
            "crosshair_style": self.crosshair_style_combobox.currentData(),
            "crosshair_size": self.crosshair_size_spinbox.value(),
            "crosshair_color": self.crosshair_color_edit.text(),
            "teleprompter_speed": self.teleprompter_speed_spinbox.value(),
            "teleprompter_font": self.teleprompter_font_spinbox.value(),
            "teleprompter_mirror": self.teleprompter_mirror_checkbox.isChecked(),
            "teleprompter_script": self.teleprompter_edit.toPlainText(),
        }

    def set_state(self, state: dict) -> None:
        style = state.get("crosshair_style")
        if style is not None:
            index = self.crosshair_style_combobox.findData(str(style))
            if index >= 0:
                self.crosshair_style_combobox.setCurrentIndex(index)
        for spinbox, key in ((self.crosshair_size_spinbox, "crosshair_size"),
                             (self.teleprompter_speed_spinbox, "teleprompter_speed"),
                             (self.teleprompter_font_spinbox, "teleprompter_font")):
            value = coerce_int(state.get(key))
            if value is not None:
                spinbox.setValue(max(spinbox.minimum(), min(spinbox.maximum(), value)))
        if state.get("crosshair_color"):
            self.crosshair_color_edit.setText(str(state["crosshair_color"]))
        if "teleprompter_mirror" in state:
            self.teleprompter_mirror_checkbox.setChecked(bool(state["teleprompter_mirror"]))
        if state.get("teleprompter_script") is not None:
            self.teleprompter_edit.setPlainText(str(state["teleprompter_script"]))
