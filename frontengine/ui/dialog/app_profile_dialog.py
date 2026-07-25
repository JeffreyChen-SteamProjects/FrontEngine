"""
程式對應預設集：切到某個程式時自動套用一組覆蓋層設定（例如打開剪輯軟體
就換成「工作」那組）。左欄填程式名稱，右欄挑一個已儲存的預設集。

Per-app profiles: apply a saved preset when a given app takes focus - the
"work" set when the editor comes up. The left column is the app name, the right
column picks one of your saved presets.
"""
from __future__ import annotations

from typing import Dict, Optional

from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QGridLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QWidget,
)

from frontengine.user_setting.preset_repository import PresetRepository
from frontengine.user_setting.user_setting_file import user_setting_dict, write_user_setting
from frontengine.utils.app_profile.app_profile_service import normalize_profiles
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.smart_pause.pause_rules import normalize_app_name


def _t(key: str, fallback: str) -> str:
    return language_wrapper.language_word_dict.get(key, fallback)


def current_profiles() -> Dict[str, str]:
    """目前設定裡的 {程式: 預設集} 對照表。"""
    return normalize_profiles(user_setting_dict.get("app_profiles"))


class AppProfileDialog(QDialog):
    """編輯「程式 → 預設集」對照表。"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        front_engine_logger.info("[AppProfileDialog] Init")
        super().__init__(parent)
        self.setWindowTitle(_t("app_profile_title", "App profiles"))
        self.presets = PresetRepository().list_presets()

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels([
            _t("app_profile_app_column", "Application"),
            _t("app_profile_preset_column", "Preset"),
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.add_button = QPushButton(_t("app_profile_add", "Add"))
        self.add_button.clicked.connect(lambda: self.add_row("", ""))
        self.remove_button = QPushButton(_t("app_profile_remove", "Remove"))
        self.remove_button.clicked.connect(self.remove_selected_row)
        self.hint_label = QLabel(
            _t("app_profile_hint",
               "Presets are saved from the Presets menu. Without any saved preset "
               "there is nothing to apply."))
        self.hint_label.setWordWrap(True)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout = QGridLayout(self)
        layout.addWidget(self.table, 0, 0, 1, 2)
        layout.addWidget(self.add_button, 1, 0)
        layout.addWidget(self.remove_button, 1, 1)
        layout.addWidget(self.hint_label, 2, 0, 1, 2)
        layout.addWidget(self.button_box, 3, 0, 1, 2)

        for app, preset in current_profiles().items():
            self.add_row(app, preset)

    def add_row(self, app: str = "", preset: str = "") -> None:
        """加一列（預設集下拉選單列出所有已儲存的預設集）。"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(str(app)))
        combobox = QComboBox()
        combobox.addItems(self.presets)
        # 設定裡指到已被刪掉的預設集時，仍把名稱留著讓使用者看得到
        # Keep a name that points at a deleted preset visible instead of silently
        # swapping it for another one.
        if preset and preset not in self.presets:
            combobox.addItem(str(preset))
        if preset:
            combobox.setCurrentText(str(preset))
        self.table.setCellWidget(row, 1, combobox)

    def remove_selected_row(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def profiles(self) -> Dict[str, str]:
        """目前表格上的對照表（空白列會被略過）。"""
        profiles: Dict[str, str] = {}
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            combobox = self.table.cellWidget(row, 1)
            app = normalize_app_name(item.text() if item else "")
            preset = combobox.currentText().strip() if combobox else ""
            if app and preset:
                profiles[app] = preset
        return profiles

    def accept(self) -> None:
        profiles = self.profiles()
        user_setting_dict["app_profiles"] = profiles
        write_user_setting()
        front_engine_logger.info(f"[AppProfileDialog] saved | {profiles}")
        super().accept()
