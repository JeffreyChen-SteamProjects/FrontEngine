"""
看板模式設定：依序輪播一組預設集，適合把機器擺著當展示螢幕。

Signage settings: rotate through a set of presets, for a machine left running
as a display.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QGridLayout, QLabel, QPlainTextEdit, QSpinBox, QWidget,
)

from frontengine.user_setting.user_setting_file import user_setting_dict, write_user_setting
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import retranslator
from frontengine.utils.signage.signage_service import (
    DEFAULT_INTERVAL_MINUTES, MAX_INTERVAL_MINUTES, MIN_INTERVAL_MINUTES, clamp_interval,
    normalize_playlist,
)

SETTING_KEY = "signage"
DEFAULT_SETTINGS: Dict[str, Any] = {
    "enabled": False, "presets": [], "interval_minutes": DEFAULT_INTERVAL_MINUTES,
    "hide_window": True,
}


def _t(key: str, fallback: str) -> str:
    return language_wrapper.language_word_dict.get(key, fallback)


def current_settings() -> Dict[str, Any]:
    """目前的看板設定（缺項目補預設值）。"""
    stored = user_setting_dict.get(SETTING_KEY)
    settings = dict(DEFAULT_SETTINGS)
    if isinstance(stored, dict):
        settings.update({key: stored[key] for key in DEFAULT_SETTINGS if key in stored})
    settings["presets"] = normalize_playlist(settings.get("presets"))
    settings["interval_minutes"] = clamp_interval(settings.get("interval_minutes"))
    return settings


class SignageDialog(QDialog):
    """設定要輪播哪些預設集、多久換一次。"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        front_engine_logger.info("[SignageDialog] Init")
        super().__init__(parent)
        self.setWindowTitle(_t("signage_title", "Signage mode"))
        settings = current_settings()

        self.enable_checkbox = QCheckBox(_t("signage_enable", "Rotate presets"))
        retranslator.bind(self.enable_checkbox, "signage_enable", "Rotate presets")
        self.enable_checkbox.setChecked(bool(settings.get("enabled")))
        self.presets_label = QLabel(_t("signage_presets_label", "Presets, one per line:"))
        retranslator.bind(self.presets_label, "signage_presets_label", "Presets, one per line:")
        self.presets_edit = QPlainTextEdit("\n".join(settings.get("presets", [])))
        self.interval_label = QLabel(_t("signage_interval_label", "Change every (minutes)"))
        retranslator.bind(self.interval_label, "signage_interval_label", "Change every (minutes)")
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setRange(MIN_INTERVAL_MINUTES, MAX_INTERVAL_MINUTES)
        self.interval_spinbox.setValue(settings.get("interval_minutes"))
        self.hide_checkbox = QCheckBox(
            _t("signage_hide_window", "Hide the main window while rotating"))
        retranslator.bind(self.hide_checkbox, "signage_hide_window", "Hide the main window while rotating")
        self.hide_checkbox.setChecked(bool(settings.get("hide_window", True)))
        self.hint_label = QLabel(
            _t("signage_hint",
               "Presets are saved from the Presets menu. The rotation wraps at the end, so a "
               "machine left running keeps cycling."))
        retranslator.bind(self.hint_label, "signage_hint", "Presets are saved from the Presets menu. The rotation wraps at the end, so a " "machine left running keeps cycling.")
        self.hint_label.setWordWrap(True)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout = QGridLayout(self)
        layout.addWidget(self.enable_checkbox, 0, 0, 1, 2)
        layout.addWidget(self.presets_label, 1, 0, 1, 2)
        layout.addWidget(self.presets_edit, 2, 0, 1, 2)
        layout.addWidget(self.interval_label, 3, 0)
        layout.addWidget(self.interval_spinbox, 3, 1)
        layout.addWidget(self.hide_checkbox, 4, 0, 1, 2)
        layout.addWidget(self.hint_label, 5, 0, 1, 2)
        layout.addWidget(self.button_box, 6, 0, 1, 2)

    def settings(self) -> Dict[str, Any]:
        """對話框上目前的設定。"""
        return {
            "enabled": self.enable_checkbox.isChecked(),
            "presets": normalize_playlist(self.presets_edit.toPlainText()),
            "interval_minutes": self.interval_spinbox.value(),
            "hide_window": self.hide_checkbox.isChecked(),
        }

    def accept(self) -> None:
        settings = self.settings()
        user_setting_dict[SETTING_KEY] = settings
        write_user_setting()
        front_engine_logger.info(f"[SignageDialog] saved | {len(settings['presets'])} preset(s)")
        super().accept()
