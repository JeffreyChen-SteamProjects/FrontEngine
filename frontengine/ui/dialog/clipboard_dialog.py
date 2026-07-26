"""
剪貼簿歷史視窗：搜尋、釘選、貼回去。

預設不記錄；要記錄得自己在這裡打開。除非再額外勾選「保存到檔案」，否則
內容只留在記憶體，關掉程式就沒了——剪貼簿裡常有密碼，這是刻意的預設。

The clipboard history window: search, pin, put back.

Recording is off until switched on here, and unless "keep between sessions" is
also ticked the history lives in memory only and is gone when the app closes.
Clipboards routinely hold passwords; that default is deliberate.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QDialog, QDialogButtonBox, QGridLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QWidget,
)

from frontengine.user_setting.user_setting_file import user_setting_dict, write_user_setting
from frontengine.utils.clipboard.clipboard_history import ClipboardHistory, preview
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import retranslator

_PIN_MARK = "📌 "


def _t(key: str, fallback: str) -> str:
    return language_wrapper.language_word_dict.get(key, fallback)


class ClipboardDialog(QDialog):
    """瀏覽剪貼簿歷史並貼回去。"""

    def __init__(self, history: ClipboardHistory, parent: Optional[QWidget] = None) -> None:
        front_engine_logger.info("[ClipboardDialog] Init")
        super().__init__(parent)
        self.setWindowTitle(_t("clipboard_title", "Clipboard history"))
        self.history = history

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(_t("clipboard_search", "Search..."))
        self.search_edit.textChanged.connect(self.reload_entries)

        self.entry_list = QListWidget()
        self.entry_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.entry_list.itemDoubleClicked.connect(lambda _item: self.copy_selected())

        self.copy_button = QPushButton(_t("clipboard_copy", "Copy"))
        retranslator.bind(self.copy_button, "clipboard_copy", "Copy")
        self.copy_button.clicked.connect(self.copy_selected)
        self.pin_button = QPushButton(_t("clipboard_pin", "Pin / unpin"))
        retranslator.bind(self.pin_button, "clipboard_pin", "Pin / unpin")
        self.pin_button.clicked.connect(self.toggle_pin_selected)
        self.remove_button = QPushButton(_t("clipboard_remove", "Remove"))
        retranslator.bind(self.remove_button, "clipboard_remove", "Remove")
        self.remove_button.clicked.connect(self.remove_selected)
        self.clear_button = QPushButton(_t("clipboard_clear", "Clear (keep pinned)"))
        retranslator.bind(self.clear_button, "clipboard_clear", "Clear (keep pinned)")
        self.clear_button.clicked.connect(self.clear_history)

        self.persist_checkbox = QCheckBox(
            _t("clipboard_persist", "Keep this history between sessions"))
        retranslator.bind(self.persist_checkbox, "clipboard_persist", "Keep this history between sessions")
        self.persist_checkbox.setChecked(bool(user_setting_dict.get("clipboard_persist")))
        self.persist_checkbox.toggled.connect(self._store_persist)
        self.hint_label = QLabel(
            _t("clipboard_hint",
               "History stays on this machine and is never sent anywhere. Unless you tick "
               "the box above it is kept in memory only, because clipboards often hold "
               "passwords."))
        retranslator.bind(self.hint_label, "clipboard_hint", "History stays on this machine and is never sent anywhere. Unless you tick " "the box above it is kept in memory only, because clipboards often hold " "passwords.")
        self.hint_label.setWordWrap(True)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.rejected.connect(self.reject)

        layout = QGridLayout(self)
        layout.addWidget(self.search_edit, 0, 0, 1, 4)
        layout.addWidget(self.entry_list, 1, 0, 1, 4)
        layout.addWidget(self.copy_button, 2, 0)
        layout.addWidget(self.pin_button, 2, 1)
        layout.addWidget(self.remove_button, 2, 2)
        layout.addWidget(self.clear_button, 2, 3)
        layout.addWidget(self.persist_checkbox, 3, 0, 1, 4)
        layout.addWidget(self.hint_label, 4, 0, 1, 4)
        layout.addWidget(self.button_box, 5, 0, 1, 4)

        self.reload_entries()

    def reload_entries(self) -> int:
        """依搜尋字串重畫清單，回傳顯示的筆數。"""
        self.entry_list.clear()
        for entry in self.history.search(self.search_edit.text()):
            label = (_PIN_MARK if entry["pinned"] else "") + preview(entry["text"])
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, entry["text"])
            item.setToolTip(entry["text"])
            self.entry_list.addItem(item)
        return self.entry_list.count()

    def selected_text(self) -> Optional[str]:
        item = self.entry_list.currentItem()
        if item is None:
            return None
        return str(item.data(Qt.ItemDataRole.UserRole))

    def copy_selected(self) -> bool:
        """把選到的內容放回剪貼簿。"""
        text = self.selected_text()
        if text is None:
            return False
        clipboard = QGuiApplication.clipboard()
        if clipboard is None:  # pragma: no cover - no clipboard at all
            return False
        clipboard.setText(text)
        return True

    def toggle_pin_selected(self) -> bool:
        text = self.selected_text()
        if text is None:
            return False
        current = next((entry for entry in self.history.entries if entry["text"] == text), None)
        if current is None:
            return False
        self.history.set_pinned(text, not current["pinned"])
        self.reload_entries()
        return True

    def remove_selected(self) -> bool:
        text = self.selected_text()
        if text is None:
            return False
        removed = self.history.remove(text)
        self.reload_entries()
        return removed

    def clear_history(self) -> None:
        """清空未釘選的紀錄。"""
        self.history.clear(keep_pinned=True)
        self.reload_entries()

    def _store_persist(self, enabled: bool) -> None:
        user_setting_dict["clipboard_persist"] = bool(enabled)
        if not enabled:
            # 取消保存時把已經寫下去的內容一併移除，不留殘影
            # Turning saving off also clears what was already written down.
            user_setting_dict["clipboard_entries"] = []
        write_user_setting()
