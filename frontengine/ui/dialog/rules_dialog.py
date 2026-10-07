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
import json
import uuid
from copy import deepcopy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QGridLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QWidget,
    QPlainTextEdit,
)

from frontengine.user_setting.user_setting_file import user_setting_dict, write_user_setting
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import tr, retranslator, translate
from frontengine.utils.rules.rule_engine import (
    ACTION_APPLY_PRESET, ACTIONS, VALUE_ACTIONS, normalize_rule, normalize_rules,
    RuleEngineService,
)

from frontengine.utils.actions.action_registry import ACTION_LABELS

SETTING_KEY = "overlay_rules"

_COLUMN_LABEL = 0
_COLUMN_DAYS = 1
_COLUMN_FROM = 2
_COLUMN_TO = 3
_COLUMN_APPS = 4
_COLUMN_ACTION = 5
_COLUMN_VALUE = 6
_COLUMN_PRIORITY = 7
_COLUMN_COOLDOWN = 8

_DAY_LETTERS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_ACTION_LABELS = tuple((action, *ACTION_LABELS[action]) for action in ACTIONS)


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
        self.service = getattr(parent, 'rule_engine_service', None) or RuleEngineService(parent=self)
        self._build_table()
        self._build_edit_buttons()
        self._build_diagnostics()
        self._build_layout()
        for rule in current_rules():
            self.add_row(rule)
        retranslator.bind(self, 'rules_title', setter='setWindowTitle')
        retranslator.bind_call(self._retranslate)

    def _build_table(self) -> None:
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            _t("rules_column_label", "Rule"),
            _t("rules_column_days", "Days"),
            _t("rules_column_from", "From"),
            _t("rules_column_to", "To"),
            _t("rules_column_apps", "Apps"),
            _t("rules_column_action", "Do"),
            _t("rules_column_value", "With"),
            _t('rules_priority', 'Priority'),
            _t('rules_cooldown', 'Cooldown (seconds)'),
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)

    def _build_edit_buttons(self) -> None:
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
    def _build_diagnostics(self) -> None:
        self.preview_button = tr(QPushButton(), 'rules_preview')
        self.history_button = tr(QPushButton(), 'rules_history')
        self.preview_button.clicked.connect(self.preview_conditions)
        self.history_button.clicked.connect(self.refresh_history)
        self.preview_button.setAutoDefault(False)
        self.history_button.setAutoDefault(False)
        self.diagnostics = QPlainTextEdit()
        self.diagnostics.setReadOnly(True)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.order_hint = tr(QLabel(), 'rules_order_hint')
        self.order_hint.setWordWrap(True)

    def _build_layout(self) -> None:
        layout = QGridLayout(self)
        layout.addWidget(self.table, 0, 0, 1, 2)
        layout.addWidget(self.add_button, 1, 0)
        layout.addWidget(self.remove_button, 1, 1)
        layout.addWidget(self.hint_label, 2, 0, 1, 2)
        layout.addWidget(self.order_hint, 3, 0, 1, 2)
        layout.addWidget(self.preview_button, 4, 0)
        layout.addWidget(self.history_button, 4, 1)
        layout.addWidget(self.diagnostics, 5, 0, 1, 2)
        layout.addWidget(self.status, 6, 0, 1, 2)
        layout.addWidget(self.button_box, 7, 0, 1, 2)
        self.resize(1050, 700)


    def add_row(self, rule: Optional[Dict[str, Any]] = None) -> None:
        """加一列；沒給資料就給一筆空白的規則。"""
        entry = rule or {"label": "", "enabled": True, "action": ACTION_APPLY_PRESET,
                         "value": "", "when": {}}
        condition = entry.get("when") or {}
        row = self.table.rowCount()
        self.table.insertRow(row)

        label_item = QTableWidgetItem(str(entry.get("label", "")))
        label_item.setData(Qt.ItemDataRole.UserRole, {
            'id': entry.get('id') or uuid.uuid4().hex, 'when': deepcopy(condition)})
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
        self.table.setItem(row, _COLUMN_PRIORITY, QTableWidgetItem(str(entry.get('priority', 0))))
        self.table.setItem(row, _COLUMN_COOLDOWN, QTableWidgetItem(str(entry.get('cooldown', 0))))

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
        metadata = label_item.data(Qt.ItemDataRole.UserRole) or {}
        return normalize_rule({
            'id': metadata.get('id'),
            "label": label_item.text().strip(),
            "enabled": label_item.checkState() == Qt.CheckState.Checked,
            "action": action,
            # 不需要附帶值的動作把值丟掉，免得使用者換過動作之後留下一個
            # 看不到作用、卻會被存起來的殘值。
            # Actions that take no value drop it, so switching action does not
            # leave a saved leftover that does nothing.
            "value": self._cell_text(row, _COLUMN_VALUE) if action in VALUE_ACTIONS else "",
            'priority': self._cell_text(row, _COLUMN_PRIORITY),
            'cooldown': self._cell_text(row, _COLUMN_COOLDOWN),
            "when": {
                **metadata.get('when', {}),
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
        if self.table.rowCount() > 200 or any(
                self._cell_text(row, _COLUMN_LABEL) and self._row_entry(row) is None
                for row in range(self.table.rowCount())):
            self.status.setText(translate('rules_invalid_rows'))
            return
        old = user_setting_dict.get(SETTING_KEY)
        user_setting_dict[SETTING_KEY] = rules
        try:
            write_user_setting()
        except (OSError, ValueError) as error:
            if old is None:
                user_setting_dict.pop(SETTING_KEY, None)
            else:
                user_setting_dict[SETTING_KEY] = old
            self.status.setText(str(error))
            return
        front_engine_logger.info(f"[RulesDialog] saved | {len(rules)} rule(s)")
        super().accept()

    def _retranslate(self) -> None:
        keys = ('rules_column_label', 'rules_column_days', 'rules_column_from', 'rules_column_to',
                'rules_column_apps', 'rules_column_action', 'rules_column_value', 'rules_priority', 'rules_cooldown')
        self.table.setHorizontalHeaderLabels([translate(key) for key in keys])
        for row in range(self.table.rowCount()):
            combo = self.table.cellWidget(row, _COLUMN_ACTION)
            for index, (_action, key, fallback) in enumerate(_ACTION_LABELS):
                combo.setItemText(index, translate(key, fallback))

    def preview_conditions(self) -> None:
        """Preview unsaved rows using current context without running any actions."""
        try:
            rows = self.service.preview(self.rules())
            self._display_diagnostics(rows)
            self.status.setText(translate('rules_preview_hint'))
        except (OSError, ValueError, RuntimeError) as error:
            self.status.setText(str(error))

    def refresh_history(self) -> None:
        """Show bounded in-memory trigger/cooldown/application receipts."""
        self._display_diagnostics(list(self.service.history))
        self.status.setText(translate('rules_history_hint'))

    def _display_diagnostics(self, rows: list) -> None:
        """Show editable rule values and evidence, excluding internal identities."""
        self.diagnostics.setPlainText('\n\n'.join(self._entry_summary(entry) for entry in rows))

    def _entry_summary(self, entry: dict) -> str:
        rule = entry['rule']
        if 'matches' in entry:
            result = translate('rules_matched' if entry['matches'] else 'rules_unmatched')
            result += f" · matches={entry['matches']} · active={entry['active']}"
        else:
            result = translate('rules_receipt_' + entry['status'], entry['status'])
        key, fallback = ACTION_LABELS[rule['action']]
        lines = [f"{rule['label']} · {result}",
                 f"{translate(key, fallback)}: {rule['value']}",
                 f"{translate('rules_priority')}: {rule['priority']} · "
                 f"{translate('rules_cooldown')}: {rule['cooldown']} · "
                 f"{translate('rules_remaining')}: {entry.get('cooldown_remaining', entry.get('remaining', 0)):.1f}"]
        condition = deepcopy(rule['when'])
        condition['days'] = format_days(condition.get('days'))
        condition['from'] = format_minute(condition.get('from'))
        condition['to'] = format_minute(condition.get('to'))
        condition = {key: value for key, value in condition.items() if value is not None and value != '' and value != []}
        lines.append(translate('rules_conditions') + ': ' + json.dumps(condition, ensure_ascii=False))
        lines.append(translate('rules_context') + ': ' + json.dumps(entry['context'], ensure_ascii=False))
        if entry.get('at'):
            lines.insert(0, entry['at'])
        if entry.get('error'):
            lines.append(entry['error'])
        return '\n'.join(lines)
