"""
使用時間報告：今天各程式用了多久，以及最近七天的總量。

這份資料只存在本機的 frontengine_usage.json，不會傳到任何地方；統計預設關閉，
而且這裡就有「清除」按鈕，按下去連檔案一起刪掉。

The usage report: how long each app had focus today, plus the last seven days.

The data lives only in the local frontengine_usage.json and goes nowhere else.
Tracking is off by default, and the clear button here deletes the file itself.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QGridLayout, QHeaderView, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QWidget,
)

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import tr
from frontengine.utils.usage_tracking.usage_tracker import UsageTracker, format_duration


def _t(key: str, fallback: str) -> str:
    return language_wrapper.language_word_dict.get(key, fallback)


def share_percent(seconds: float, total: float) -> int:
    """某個程式佔今天的百分比；今天還沒有紀錄就是 0。"""
    if total <= 0:
        return 0
    return int(round(max(0.0, min(1.0, seconds / total)) * 100))


class UsageReportDialog(QDialog):
    """顯示今天的使用時間，並提供開關與清除。"""

    def __init__(self, tracker: UsageTracker, parent: Optional[QWidget] = None,
                 enabled: bool = False, on_toggle=None, on_clear=None) -> None:
        front_engine_logger.info("[UsageReportDialog] Init")
        super().__init__(parent)
        self.setWindowTitle(_t("usage_title", "Screen time"))
        self.tracker = tracker
        self._on_toggle = on_toggle
        self._on_clear = on_clear

        self.enable_checkbox = tr(QCheckBox(), "usage_enable", "Track which apps I use")
        self.enable_checkbox.setChecked(bool(enabled))
        self.enable_checkbox.toggled.connect(self._toggle)

        self.total_label = QLabel()
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([
            _t("usage_app_column", "Application"),
            _t("usage_time_column", "Time"),
            _t("usage_share_column", "Share"),
        ])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)

        self.week_label = QLabel()
        self.week_label.setWordWrap(True)
        self.refresh_button = tr(QPushButton(), "usage_refresh", "Refresh")
        self.refresh_button.clicked.connect(self.reload_report)
        self.clear_button = tr(QPushButton(), "usage_clear", "Clear history")
        self.clear_button.clicked.connect(self.clear_history)
        self.hint_label = tr(QLabel(), "usage_hint",
            "This is stored on this machine only and is never sent anywhere. "
            "Clearing deletes the file itself.")
        self.hint_label.setWordWrap(True)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.rejected.connect(self.reject)

        layout = QGridLayout(self)
        layout.addWidget(self.enable_checkbox, 0, 0, 1, 2)
        layout.addWidget(self.total_label, 1, 0, 1, 2)
        layout.addWidget(self.table, 2, 0, 1, 2)
        layout.addWidget(self.week_label, 3, 0, 1, 2)
        layout.addWidget(self.refresh_button, 4, 0)
        layout.addWidget(self.clear_button, 4, 1)
        layout.addWidget(self.hint_label, 5, 0, 1, 2)
        layout.addWidget(self.button_box, 6, 0, 1, 2)

        self.reload_report()

    def reload_report(self) -> int:
        """重畫今天的排行，回傳列數。"""
        total = self.tracker.total_seconds()
        self.total_label.setText(
            _t("usage_total", "Today: {total}").format(total=format_duration(total)))
        rows = self.tracker.top_apps(limit=12)
        self.table.setRowCount(len(rows))
        for index, (app, seconds) in enumerate(rows):
            self.table.setItem(index, 0, QTableWidgetItem(app))
            self.table.setItem(index, 1, QTableWidgetItem(format_duration(seconds)))
            self.table.setItem(index, 2, QTableWidgetItem(f"{share_percent(seconds, total)}%"))
        self.week_label.setText(self.week_summary())
        return len(rows)

    def week_summary(self) -> str:
        """最近七天的一行摘要。"""
        parts = [f"{day[5:]} {format_duration(seconds)}"
                 for day, seconds in self.tracker.recent_days(7)]
        return "  ·  ".join(parts)

    def clear_history(self) -> None:
        """清掉所有統計（含磁碟上的檔案）。"""
        self.tracker.clear()
        if self._on_clear is not None:
            self._on_clear()
        self.reload_report()

    def _toggle(self, enabled: bool) -> None:
        if self._on_toggle is not None:
            self._on_toggle(bool(enabled))
