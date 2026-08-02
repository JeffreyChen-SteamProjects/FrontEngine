"""
條件式規則設定：「當 <條件> 成立時，做 <動作>」。

一列就是一條規則。條件欄位留白代表「不限」，所以只填時間就是純時段規則，
只填程式就是純程式規則——不必為了每一種組合各開一個對話框，那正是這個功能
存在的原因。

Conditional rule settings: "when <conditions> hold, do <action>".

One row per rule. A blank condition means "any", so filling in only the time
gives a time rule and only the app gives an app rule - no dialog per
combination, which is the whole point of the feature.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QGridLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QWidget,
)

from frontengine.user_setting.user_setting_file import user_setting_dict, write_user_setting
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import tr
from frontengine.utils.rules.rule_engine import (
    ACTION_APPLY_PRESET, ACTION_CLOSE_ALL, ACTION_HIDE_ALL, ACTION_QUALITY_TIER,
    ACTION_SHOW_ALL, VALUE_ACTIONS, normalize_rule, normalize_rules,
)

SETTING_KEY = "overlay_rules"

_COLUMN_LABEL = 0
_COLUMN_DAYS = 1
_COLUMN_FROM = 2
_COLUMN_TO = 3
_COLUMN_APPS = 4
_COLUMN_ACTION = 5
_COLUMN_VALUE = 6

_DAY_LETTERS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_ACTION_LABELS = (
    (ACTION_APPLY_PRESET, "rules_action_apply_preset", "Apply preset"),
    (ACTION_HIDE_ALL, "control_center_hide_all", "Hide all"),
    (ACTION_SHOW_ALL, "control_center_show_all", "Show all"),
    (ACTION_CLOSE_ALL, "control_center_close_all", "Close all"),
    (ACTION_QUALITY_TIER, "rules_action_quality", "Set quality"),
)


def _t(key: str, fallback: str) -> str:
    return language_wrapper.language_word_dict.get(key, fallback)


def current_rules() -> List[Dict[str, Any]]:
    """目前設定裡的規則（壞掉的項目會被跳過）。"""
    return normalize_rules(user_setting_dict.get(SETTING_KEY))


def format_days(days: Any) -> str:
    """把 [0, 1, 4] 寫成 "Mon,Tue,Fri"；空的寫成空字串（＝每天）。"""
    return ",".join(_DAY_LETTERS[day] for day in days or () if 0 <= day <= 6)


def parse_days(text: Any) -> List[int]:
    """
    把 "Mon,Tue" 或 "0,1" 解析成星期清單。兩種寫法都收：使用者會照著看到的
    格式改，也會直接打數字。
    Parse "Mon,Tue" or "0,1" into weekdays. Both are accepted: people edit what
    they see, and people type numbers.
    """
    days = []
    for token in str(text or "").replace(";", ",").split(","):
        item = token.strip()
        if not item:
            continue
        if item.isdigit():
            days.append(int(item))
            continue
        lowered = item[:3].lower()
        for index, name in enumerate(_DAY_LETTERS):
            if name.lower() == lowered:
                days.append(index)
                break
    return days


def format_minute(minute: Optional[int]) -> str:
    """把午夜起算的分鐘數寫回 "HH:MM"；None 寫成空字串。"""
    if minute is None:
        return ""
    return f"{minute // 60:02d}:{minute % 60:02d}"


class RulesDialog(QDialog):
    """編輯條件式規則清單。"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        front_engine_logger.info("[RulesDialog] Init")
        super().__init__(parent)
        self.setWindowTitle(_t("rules_title", "Rules"))

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            _t("rules_column_label", "Rule"),
            _t("rules_column_days", "Days"),
            _t("rules_column_from", "From"),
            _t("rules_column_to", "To"),
            _t("rules_column_apps", "Apps"),
            _t("rules_column_action", "Do"),
            _t("rules_column_value", "With"),
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.add_button = tr(QPushButton(), "rules_add", "Add")
        self.add_button.clicked.connect(lambda: self.add_row())
        self.remove_button = tr(QPushButton(), "rules_remove", "Remove")
        self.remove_button.clicked.connect(self.remove_selected_row)
        self.hint_label = tr(QLabel(), "rules_hint",
            "Tick a row to keep it active. Leave a condition blank for \"any\". Days "
            "are Mon,Tue,...; times are 24-hour like 19:30 and may cross midnight. A "
            "rule runs once when its conditions start holding, not repeatedly while "
            "they hold.")
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

        for rule in current_rules():
            self.add_row(rule)

    def add_row(self, rule: Optional[Dict[str, Any]] = None) -> None:
        """加一列；沒給資料就給一筆空白的規則。"""
        entry = rule or {"label": "", "enabled": True, "action": ACTION_APPLY_PRESET,
                         "value": "", "when": {}}
        condition = entry.get("when") or {}
        row = self.table.rowCount()
        self.table.insertRow(row)

        label_item = QTableWidgetItem(str(entry.get("label", "")))
        label_item.setFlags(label_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        label_item.setCheckState(Qt.CheckState.Checked if entry.get("enabled", True)
                                 else Qt.CheckState.Unchecked)
        self.table.setItem(row, _COLUMN_LABEL, label_item)
        self.table.setItem(row, _COLUMN_DAYS,
                           QTableWidgetItem(format_days(condition.get("days"))))
        self.table.setItem(row, _COLUMN_FROM,
                           QTableWidgetItem(format_minute(condition.get("from"))))
        self.table.setItem(row, _COLUMN_TO,
                           QTableWidgetItem(format_minute(condition.get("to"))))
        self.table.setItem(row, _COLUMN_APPS,
                           QTableWidgetItem(", ".join(condition.get("apps") or ())))

        action_combobox = QComboBox()
        for action, key, fallback in _ACTION_LABELS:
            action_combobox.addItem(_t(key, fallback), action)
        index = action_combobox.findData(entry.get("action", ACTION_APPLY_PRESET))
        action_combobox.setCurrentIndex(max(0, index))
        self.table.setCellWidget(row, _COLUMN_ACTION, action_combobox)

        self.table.setItem(row, _COLUMN_VALUE, QTableWidgetItem(str(entry.get("value", ""))))

    def remove_selected_row(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def _cell_text(self, row: int, column: int) -> str:
        item = self.table.item(row, column)
        return item.text().strip() if item else ""

    def _row_entry(self, row: int) -> Optional[Dict[str, Any]]:
        label_item = self.table.item(row, _COLUMN_LABEL)
        action_combobox = self.table.cellWidget(row, _COLUMN_ACTION)
        if label_item is None or action_combobox is None:
            return None
        action = action_combobox.currentData()
        return normalize_rule({
            "label": label_item.text().strip(),
            "enabled": label_item.checkState() == Qt.CheckState.Checked,
            "action": action,
            # 不需要附帶值的動作把值丟掉，免得使用者換過動作之後留下一個
            # 看不到作用、卻會被存起來的殘值。
            # Actions that take no value drop it, so switching action does not
            # leave a saved leftover that does nothing.
            "value": self._cell_text(row, _COLUMN_VALUE) if action in VALUE_ACTIONS else "",
            "when": {
                "days": parse_days(self._cell_text(row, _COLUMN_DAYS)),
                "from": self._cell_text(row, _COLUMN_FROM),
                "to": self._cell_text(row, _COLUMN_TO),
                "apps": self._cell_text(row, _COLUMN_APPS),
            },
        })

    def rules(self) -> List[Dict[str, Any]]:
        """目前表格上的規則（不完整的列會被略過）。"""
        rules = []
        for row in range(self.table.rowCount()):
            entry = self._row_entry(row)
            if entry is not None:
                rules.append(entry)
        return rules

    def accept(self) -> None:
        rules = self.rules()
        user_setting_dict[SETTING_KEY] = rules
        write_user_setting()
        front_engine_logger.info(f"[RulesDialog] saved | {len(rules)} rule(s)")
        super().accept()
