"""
自訂提醒設定：每隔一段時間提醒一次（喝水、起來走走），或每天在固定時間
提醒一次（會議、吃藥）。提醒會以畫面上方的提示卡顯示。

Custom reminder settings: every N minutes (drink water, stand up) or once a day
at a set time (a meeting, a pill). Reminders appear as a toast near the top of
the screen.
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
from frontengine.utils.reminder.reminder_service import (
    DEFAULT_EVERY_MINUTES, KIND_AT, KIND_EVERY, normalize_reminder, normalize_reminders,
    parse_time_of_day,
)

_COLUMN_LABEL = 0
_COLUMN_KIND = 1
_COLUMN_VALUE = 2


def _t(key: str, fallback: str) -> str:
    return language_wrapper.language_word_dict.get(key, fallback)


def current_reminders() -> List[Dict[str, Any]]:
    """目前設定裡的提醒清單（壞掉的項目會被跳過）。"""
    return normalize_reminders(user_setting_dict.get("reminders"))


class ReminderDialog(QDialog):
    """編輯自訂提醒清單。"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        front_engine_logger.info("[ReminderDialog] Init")
        super().__init__(parent)
        self.setWindowTitle(_t("reminder_title", "Reminders"))

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([
            _t("reminder_label_column", "Reminder"),
            _t("reminder_kind_column", "When"),
            _t("reminder_value_column", "Minutes / time"),
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.add_button = tr(QPushButton(), "reminder_add", "Add")
        self.add_button.clicked.connect(lambda: self.add_row())
        self.remove_button = tr(QPushButton(), "reminder_remove", "Remove")
        self.remove_button.clicked.connect(self.remove_selected_row)
        self.hint_label = tr(QLabel(), "reminder_hint",
            "Tick a row to keep it active. \"Every\" takes minutes, \"At\" takes a "
            "24-hour time such as 14:30.")
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

        for reminder in current_reminders():
            self.add_row(reminder)

    def add_row(self, reminder: Optional[Dict[str, Any]] = None) -> None:
        """加一列；沒給資料就給一筆空白的「每 45 分鐘」。"""
        entry = reminder or {"label": "", "kind": KIND_EVERY, "minutes": 45, "enabled": True}
        row = self.table.rowCount()
        self.table.insertRow(row)

        label_item = QTableWidgetItem(str(entry.get("label", "")))
        label_item.setFlags(label_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        label_item.setCheckState(Qt.CheckState.Checked if entry.get("enabled", True)
                                 else Qt.CheckState.Unchecked)
        self.table.setItem(row, _COLUMN_LABEL, label_item)

        kind_combobox = QComboBox()
        kind_combobox.addItem(_t("reminder_kind_every", "Every"), KIND_EVERY)
        kind_combobox.addItem(_t("reminder_kind_at", "At"), KIND_AT)
        kind_index = kind_combobox.findData(entry.get("kind", KIND_EVERY))
        kind_combobox.setCurrentIndex(max(0, kind_index))
        kind_combobox.currentIndexChanged.connect(
            lambda _index, box=kind_combobox: self._on_kind_changed(box))
        self.table.setCellWidget(row, _COLUMN_KIND, kind_combobox)

        value = entry.get("at") if entry.get("kind") == KIND_AT else entry.get("minutes", 45)
        self.table.setItem(row, _COLUMN_VALUE, QTableWidgetItem(str(value)))

    def _on_kind_changed(self, kind_combobox: QComboBox) -> None:
        """
        「每隔」和「在」用的是完全不同的值：一個是分鐘數，一個是 HH:MM。
        切換種類時把值換成該種類的合理預設，不然舊的值（例如 45）會解析失敗，
        整列在按下確定時被無聲丟掉——使用者只是改了下拉選單，提醒就不見了。
        "Every" and "At" take entirely different values: a minute count versus
        HH:MM. Swap in a sensible default for the new kind, or the old value (45,
        say) fails to parse and the whole row is silently dropped on OK - the
        user changed a dropdown and lost the reminder.
        """
        row = self._row_of(kind_combobox)
        if row < 0:
            return
        kind = kind_combobox.currentData()
        value_item = self.table.item(row, _COLUMN_VALUE)
        current = value_item.text().strip() if value_item else ""
        if kind == KIND_AT:
            if parse_time_of_day(current) is not None:
                return
            replacement = "09:00"
        else:
            if current.isdigit() and int(current) > 0:
                return
            replacement = str(DEFAULT_EVERY_MINUTES)
        self.table.setItem(row, _COLUMN_VALUE, QTableWidgetItem(replacement))

    def _row_of(self, widget: QComboBox) -> int:
        """這個下拉選單在第幾列（列可能被刪過，索引會變）。"""
        for row in range(self.table.rowCount()):
            if self.table.cellWidget(row, _COLUMN_KIND) is widget:
                return row
        return -1

    def remove_selected_row(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def _row_entry(self, row: int) -> Optional[Dict[str, Any]]:
        label_item = self.table.item(row, _COLUMN_LABEL)
        value_item = self.table.item(row, _COLUMN_VALUE)
        kind_combobox = self.table.cellWidget(row, _COLUMN_KIND)
        if label_item is None or kind_combobox is None:
            return None
        kind = kind_combobox.currentData()
        value = value_item.text().strip() if value_item else ""
        entry = {
            "label": label_item.text().strip(),
            "kind": kind,
            "enabled": label_item.checkState() == Qt.CheckState.Checked,
        }
        entry["at" if kind == KIND_AT else "minutes"] = value
        return normalize_reminder(entry)

    def reminders(self) -> List[Dict[str, Any]]:
        """目前表格上的提醒（格式不對的列會被略過）。"""
        reminders = []
        for row in range(self.table.rowCount()):
            entry = self._row_entry(row)
            if entry is not None:
                reminders.append(entry)
        return reminders

    def accept(self) -> None:
        reminders = self.reminders()
        user_setting_dict["reminders"] = reminders
        write_user_setting()
        front_engine_logger.info(f"[ReminderDialog] saved | {len(reminders)} reminder(s)")
        super().accept()
