"""
智慧暫停設定：決定什麼時候該把覆蓋層暫時收起來——全螢幕程式在前景、
改用電池供電，或指定的程式取得焦點。

Smart-pause settings: when should the overlays stand down - a fullscreen app in
front, the machine on battery, or one of your own apps taking focus.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QGridLayout, QLabel, QLineEdit, QWidget,
)

from frontengine.user_setting.user_setting_file import user_setting_dict, write_user_setting
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.smart_pause.pause_rules import DEFAULT_RULES, parse_app_list


def _t(key: str, fallback: str) -> str:
    return language_wrapper.language_word_dict.get(key, fallback)


def current_rules() -> Dict[str, Any]:
    """從設定讀出目前的暫停規則（缺項目就補上預設值）。"""
    stored = user_setting_dict.get("smart_pause_rules")
    rules = dict(DEFAULT_RULES)
    if isinstance(stored, dict):
        rules.update({key: stored[key] for key in DEFAULT_RULES if key in stored})
    rules["apps"] = parse_app_list(rules.get("apps"))
    return rules


class SmartPauseDialog(QDialog):
    """讓使用者挑選哪些情況要暫停覆蓋層。"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        front_engine_logger.info("[SmartPauseDialog] Init")
        super().__init__(parent)
        self.setWindowTitle(_t("smart_pause_title", "Smart pause"))
        rules = current_rules()

        self.fullscreen_checkbox = QCheckBox(
            _t("smart_pause_fullscreen", "Pause while a fullscreen app is running"))
        self.fullscreen_checkbox.setChecked(bool(rules.get("fullscreen", True)))
        self.battery_checkbox = QCheckBox(
            _t("smart_pause_battery", "Pause while running on battery"))
        self.battery_checkbox.setChecked(bool(rules.get("battery", False)))
        self.apps_label = QLabel(
            _t("smart_pause_apps_label", "Pause while these apps have focus:"))
        self.apps_edit = QLineEdit(", ".join(rules.get("apps", [])))
        self.apps_edit.setPlaceholderText("photoshop, premiere, blender")
        self.hint_label = QLabel(
            _t("smart_pause_hint",
               "Names are matched without the folder or .exe, so \"photoshop\" is enough."))
        self.hint_label.setWordWrap(True)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout = QGridLayout(self)
        layout.addWidget(self.fullscreen_checkbox, 0, 0, 1, 2)
        layout.addWidget(self.battery_checkbox, 1, 0, 1, 2)
        layout.addWidget(self.apps_label, 2, 0, 1, 2)
        layout.addWidget(self.apps_edit, 3, 0, 1, 2)
        layout.addWidget(self.hint_label, 4, 0, 1, 2)
        layout.addWidget(self.button_box, 5, 0, 1, 2)

    def rules(self) -> Dict[str, Any]:
        """目前對話框上的規則。"""
        return {
            "fullscreen": self.fullscreen_checkbox.isChecked(),
            "battery": self.battery_checkbox.isChecked(),
            "apps": parse_app_list(self.apps_edit.text()),
        }

    def accept(self) -> None:
        """寫回設定；服務每次輪詢都會重讀，不需要重啟。"""
        rules = self.rules()
        user_setting_dict["smart_pause_rules"] = rules
        write_user_setting()
        front_engine_logger.info(f"[SmartPauseDialog] saved | {rules}")
        super().accept()
