from __future__ import annotations

from typing import Dict, List, Tuple

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QWidget,
)

from frontengine.user_setting.user_setting_file import (
    get_hotkey_action_map,
    user_setting_dict,
    write_user_setting,
)
from frontengine.utils.hotkey.hotkey_service import is_valid_hotkey
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper

# 動作名稱 -> (i18n key, 英文 fallback)，用於顯示較友善的標籤
# Action name -> (i18n key, English fallback) for friendlier row labels.
_ACTION_LABELS: Dict[str, Tuple[str, str]] = {
    "close_all": ("control_center_close_all", "Close all"),
    "hide_all": ("control_center_hide_all", "Hide all"),
    "show_all": ("control_center_show_all", "Show all"),
    "mute_all": ("control_center_mute_all", "Mute all"),
    "opacity_up": ("hotkey_opacity_up", "Opacity up"),
    "opacity_down": ("hotkey_opacity_down", "Opacity down"),
    "dashboard_next": ("web_dashboard_next", "Next page"),
}


def _t(key: str, fallback: str) -> str:
    return language_wrapper.language_word_dict.get(key, fallback)


class HotkeySettingsDialog(QDialog):
    """
    讓使用者以 pynput 組合鍵語法（例如 <ctrl>+<shift>+<f12>）重新綁定全域
    快速鍵。輸入會逐一驗證，全部有效才會寫入設定並關閉。
    Rebind global hotkeys using pynput combo syntax (e.g. <ctrl>+<shift>+<f12>).
    Inputs are validated; settings are saved only when every combo is valid.
    """

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(_t("hotkey_settings_title", "Configure hotkeys"))
        layout = QGridLayout(self)

        self._edits: Dict[str, QLineEdit] = {}
        action_map = get_hotkey_action_map()

        hint = QLabel(
            _t(
                "hotkey_settings_hint",
                "Use pynput syntax, e.g. <ctrl>+<shift>+<f12>. Leave blank to unbind.",
            )
        )
        hint.setWordWrap(True)
        layout.addWidget(hint, 0, 0, 1, 2)

        for row, (action, combo) in enumerate(action_map.items(), start=1):
            key, fallback = _ACTION_LABELS.get(action, ("", action))
            layout.addWidget(QLabel(_t(key, fallback) if key else action), row, 0)
            edit = QLineEdit(combo)
            self._edits[action] = edit
            layout.addWidget(edit, row, 1)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box, len(action_map) + 1, 0, 1, 2)

    def collect_and_validate(self) -> Tuple[Dict[str, str], List[str]]:
        """
        讀取所有欄位，回傳 (有效的 動作->組合鍵, 無效動作清單)。空欄位視為解除
        綁定並略過。
        Read every field and return (valid action->combo, invalid action list).
        A blank field means "unbound" and is skipped.
        """
        bindings: Dict[str, str] = {}
        invalid: List[str] = []
        for action, edit in self._edits.items():
            combo = edit.text().strip()
            if not combo:
                continue
            if is_valid_hotkey(combo):
                bindings[action] = combo
            else:
                invalid.append(action)
        return bindings, invalid

    def _on_accept(self) -> None:
        bindings, invalid = self.collect_and_validate()
        if invalid:
            QMessageBox.warning(
                self,
                _t("hotkey_settings_title", "Configure hotkeys"),
                _t("hotkey_settings_invalid", "Invalid hotkey(s): {names}").format(
                    names=", ".join(invalid)
                ),
            )
            return
        front_engine_logger.info(f"[HotkeySettingsDialog] save | bindings={bindings}")
        user_setting_dict["hotkeys"] = bindings
        write_user_setting()
        self.accept()
