"""
遙控設定：手機網頁遙控與 MIDI 控制器。

手機遙控會在這台機器上開一個網路埠，所以預設關閉、每次啟動換新權杖、
只接受固定的動作清單——這些在畫面上都寫清楚，不藏在文件裡。

Remote control settings: the phone web remote and a MIDI controller.

The phone remote opens a network port on this machine, so it is off by default,
mints a fresh token at every start and only accepts a fixed list of actions -
all of which the dialog says out loud rather than hiding in the docs.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QGridLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QWidget,
)

from frontengine.user_setting.user_setting_file import user_setting_dict, write_user_setting
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.midi.midi_input import available as midi_available, list_devices
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import tr
from frontengine.utils.remote.remote_server import ALLOWED_ACTIONS

MIDI_KEY = "midi_bindings"
REMOTE_KEY = "phone_remote"


def _t(key: str, fallback: str) -> str:
    return language_wrapper.language_word_dict.get(key, fallback)


def current_bindings() -> Dict[str, str]:
    """設定裡的 {MIDI 鍵: 動作}，只留允許清單裡的動作。"""
    stored = user_setting_dict.get(MIDI_KEY)
    if not isinstance(stored, dict):
        return {}
    return {str(key): str(value) for key, value in stored.items()
            if str(value) in ALLOWED_ACTIONS}


def remote_enabled() -> bool:
    settings = user_setting_dict.get(REMOTE_KEY)
    return bool(settings.get("enabled")) if isinstance(settings, dict) else False


class RemoteControlDialog(QDialog):
    """設定手機遙控與 MIDI 綁定。"""

    def __init__(self, parent: Optional[QWidget] = None, remote=None, midi=None) -> None:
        front_engine_logger.info("[RemoteControlDialog] Init")
        super().__init__(parent)
        self.setWindowTitle(_t("remote_title", "Remote control"))
        self._remote = remote
        self._midi = midi
        self._learning = False

        self.remote_checkbox = tr(QCheckBox(), "remote_enable", "Let my phone control FrontEngine")
        self.remote_checkbox.setChecked(remote_enabled())
        self.remote_checkbox.toggled.connect(self._toggle_remote)
        self.remote_url_label = QLabel(self.remote_status())
        self.remote_url_label.setWordWrap(True)
        self.remote_url_label.setTextInteractionFlags(
            self.remote_url_label.textInteractionFlags().TextSelectableByMouse)
        self.remote_copy_button = tr(QPushButton(), "remote_copy", "Copy link")
        self.remote_copy_button.clicked.connect(self.copy_link)
        self.remote_hint = tr(QLabel(), "remote_hint",
            "This opens a port on this machine for your local network. The link carries a "
            "one-time token that changes every time it starts, and only the buttons on the "
            "page can be triggered - nothing else. It is plain HTTP, so treat it like any "
            "other device on your network: someone else on the same network could read the "
            "token and press the same buttons. Leave it off on networks you do not trust.")
        self.remote_hint.setWordWrap(True)

        self.midi_label = tr(QLabel(), "remote_midi_label", "MIDI controller")
        self.midi_combobox = QComboBox()
        for index, name in list_devices():
            self.midi_combobox.addItem(name, index)
        if self.midi_combobox.count() == 0:
            self.midi_combobox.addItem(_t("remote_midi_none", "No MIDI device found"), -1)
        self.learn_button = tr(QPushButton(), "remote_midi_learn", "Learn")
        self.learn_button.clicked.connect(self.start_learning)
        self.learn_button.setEnabled(midi_available())
        self.remove_button = tr(QPushButton(), "remote_midi_remove", "Remove")
        self.remove_button.clicked.connect(self.remove_selected)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels([
            _t("remote_midi_control_column", "Control"),
            _t("remote_midi_action_column", "Action"),
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout = QGridLayout(self)
        layout.addWidget(self.remote_checkbox, 0, 0, 1, 3)
        layout.addWidget(self.remote_url_label, 1, 0, 1, 2)
        layout.addWidget(self.remote_copy_button, 1, 2)
        layout.addWidget(self.remote_hint, 2, 0, 1, 3)
        layout.addWidget(self.midi_label, 3, 0)
        layout.addWidget(self.midi_combobox, 3, 1, 1, 2)
        layout.addWidget(self.table, 4, 0, 1, 3)
        layout.addWidget(self.learn_button, 5, 0)
        layout.addWidget(self.remove_button, 5, 1)
        layout.addWidget(self.button_box, 6, 0, 1, 3)

        for control, action in current_bindings().items():
            self.add_row(control, action)

    # --- phone remote ----------------------------------------------------
    def remote_status(self) -> str:
        """目前該在手機上開什麼；沒開啟就說明它是關著的。"""
        if self._remote is None or not getattr(self._remote, "running", False):
            return _t("remote_off", "Off - nothing is listening.")
        return self._remote.url()

    def copy_link(self) -> bool:
        """把連結複製起來，方便貼到手機上。"""
        if self._remote is None or not getattr(self._remote, "running", False):
            return False
        clipboard = QGuiApplication.clipboard()
        if clipboard is None:  # pragma: no cover - no clipboard at all
            return False
        clipboard.setText(self._remote.url())
        return True

    def _toggle_remote(self, enabled: bool) -> None:
        user_setting_dict[REMOTE_KEY] = {"enabled": bool(enabled)}
        write_user_setting()
        if self._remote is None:
            return
        if enabled:
            self._remote.start()
        else:
            self._remote.stop()
        self.remote_url_label.setText(self.remote_status())

    # --- MIDI bindings ---------------------------------------------------
    def add_row(self, control: str = "", action: str = "") -> None:
        """加一列綁定。"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(str(control)))
        combobox = QComboBox()
        combobox.addItems(list(ALLOWED_ACTIONS))
        if action in ALLOWED_ACTIONS:
            combobox.setCurrentText(action)
        self.table.setCellWidget(row, 1, combobox)

    def start_learning(self) -> None:
        """按下之後，下一個收到的 MIDI 訊息就會變成新的一列。"""
        self._learning = True
        self.learn_button.setText(_t("remote_midi_listening", "Press a control..."))

    @property
    def learning(self) -> bool:
        return self._learning

    def learn(self, control: str) -> bool:
        """收到 MIDI 訊息時由主視窗呼叫；沒在學習狀態就忽略。"""
        if not self._learning:
            return False
        self._learning = False
        self.learn_button.setText(_t("remote_midi_learn", "Learn"))
        self.add_row(control, ALLOWED_ACTIONS[0])
        return True

    def remove_selected(self) -> bool:
        row = self.table.currentRow()
        if row < 0:
            return False
        self.table.removeRow(row)
        return True

    def bindings(self) -> Dict[str, str]:
        """目前表格上的綁定。"""
        bindings: Dict[str, str] = {}
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            combobox = self.table.cellWidget(row, 1)
            control = item.text().strip() if item else ""
            action = combobox.currentText() if combobox else ""
            if control and action in ALLOWED_ACTIONS:
                bindings[control] = action
        return bindings

    def midi_device(self) -> Any:
        """選到的 MIDI 裝置索引。"""
        return self.midi_combobox.currentData()

    def accept(self) -> None:
        bindings = self.bindings()
        user_setting_dict[MIDI_KEY] = bindings
        user_setting_dict["midi_device"] = self.midi_device()
        write_user_setting()
        front_engine_logger.info(f"[RemoteControlDialog] saved | {len(bindings)} binding(s)")
        super().accept()
