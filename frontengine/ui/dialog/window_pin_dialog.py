"""
視窗釘選：把別的程式的視窗設成永遠在最上層，或調低它的透明度，方便一邊
對照一邊工作。只改視窗的顯示屬性，不碰內容。

Window pinning: keep another program's window on top, or fade it, so you can
work against it. Only display attributes are touched - never window content.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QDialogButtonBox, QGridLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QSlider, QWidget,
)

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import retranslator, tr
from frontengine.utils.window_pin import window_pin


def _t(key: str, fallback: str) -> str:
    return language_wrapper.language_word_dict.get(key, fallback)


class WindowPinDialog(QDialog):
    """列出目前的視窗，讓使用者釘選或調整透明度。"""

    def __init__(self, parent: Optional[QWidget] = None, lister=None) -> None:
        front_engine_logger.info("[WindowPinDialog] Init")
        super().__init__(parent)
        self.setWindowTitle(_t("window_pin_title", "Pin a window"))
        self._lister = lister or window_pin.list_windows
        self.pinned: List[int] = []
        # 只調過透明度、沒有釘選的視窗；關閉時同樣要回復成不透明
        # Windows that were faded but never pinned; they need restoring too.
        self.faded: List[int] = []

        self.window_list = QListWidget()
        self.window_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.refresh_button = tr(QPushButton(), "window_pin_refresh", "Refresh")
        self.refresh_button.clicked.connect(self.reload_windows)
        self.pin_button = tr(QPushButton(), "window_pin_pin", "Keep on top")
        self.pin_button.clicked.connect(lambda: self.apply_pin(True))
        self.unpin_button = tr(QPushButton(), "window_pin_unpin", "Release")
        self.unpin_button.clicked.connect(lambda: self.apply_pin(False))

        self.opacity_label = tr(QLabel(), "window_pin_opacity", "Opacity")
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(window_pin.MIN_OPACITY_PERCENT,
                                     window_pin.MAX_OPACITY_PERCENT)
        self.opacity_slider.setValue(window_pin.MAX_OPACITY_PERCENT)
        self.opacity_slider.valueChanged.connect(self.apply_opacity)

        hint_key, hint_fallback = (
            ("window_pin_hint",
             "Pinning changes how a window is stacked and how see-through it is. "
             "Windows only - other systems do not allow it.")
            if window_pin.available() else
            ("window_pin_unsupported", "Pinning other windows is Windows only."))
        self.hint_label = QLabel(_t(hint_key, hint_fallback))
        retranslator.bind(self.hint_label, hint_key, hint_fallback)
        self.hint_label.setWordWrap(True)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.rejected.connect(self.reject)
        self.button_box.accepted.connect(self.accept)

        layout = QGridLayout(self)
        layout.addWidget(self.window_list, 0, 0, 1, 3)
        layout.addWidget(self.refresh_button, 1, 0)
        layout.addWidget(self.pin_button, 1, 1)
        layout.addWidget(self.unpin_button, 1, 2)
        layout.addWidget(self.opacity_label, 2, 0)
        layout.addWidget(self.opacity_slider, 2, 1, 1, 2)
        layout.addWidget(self.hint_label, 3, 0, 1, 3)
        layout.addWidget(self.button_box, 4, 0, 1, 3)

        for widget in (self.pin_button, self.unpin_button, self.opacity_slider):
            widget.setEnabled(window_pin.available())
        self.reload_windows()

    def reload_windows(self) -> List[Tuple[int, str]]:
        """重新抓一次視窗清單。"""
        self.window_list.clear()
        windows = self._lister() or []
        for handle, title in windows:
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, int(handle))
            self.window_list.addItem(item)
        return windows

    def selected_handle(self) -> Optional[int]:
        """目前選到的視窗 handle；沒選就是 None。"""
        item = self.window_list.currentItem()
        if item is None:
            return None
        return int(item.data(Qt.ItemDataRole.UserRole))

    def apply_pin(self, on_top: bool) -> bool:
        """把選到的視窗釘上去或放開。"""
        handle = self.selected_handle()
        if handle is None:
            return False
        applied = window_pin.set_always_on_top(handle, on_top)
        if applied and on_top and handle not in self.pinned:
            self.pinned.append(handle)
        elif applied and not on_top and handle in self.pinned:
            self.pinned.remove(handle)
        return applied

    def apply_opacity(self) -> bool:
        """把滑桿的透明度套到選到的視窗。"""
        handle = self.selected_handle()
        if handle is None:
            return False
        applied = window_pin.set_opacity(handle, self.opacity_slider.value())
        if applied and handle not in self.faded:
            # 調過透明度的視窗也要記下來。只記「釘選過的」的話，只調透明度沒
            # 釘選的視窗永遠不會被回復——FrontEngine 關掉了，別人的視窗還是半透明。
            # Record windows we faded too. Tracking only pinned ones leaves a
            # window that was merely faded stuck that way for good: FrontEngine
            # exits and someone else's window is still see-through.
            self.faded.append(handle)
        return applied

    def release_all(self) -> None:
        """
        把這個對話框釘過的視窗全部放開並回復不透明——不然使用者關掉
        FrontEngine 之後，別人的視窗還卡在最上層或半透明。
        Release everything this dialog pinned and make it opaque again, so no
        other program is left stuck on top or faded after FrontEngine exits.
        """
        for handle in self.pinned[:]:
            window_pin.set_always_on_top(handle, False)
            window_pin.set_opacity(handle, window_pin.MAX_OPACITY_PERCENT)
        for handle in self.faded[:]:
            if handle not in self.pinned:
                window_pin.set_opacity(handle, window_pin.MAX_OPACITY_PERCENT)
        self.pinned.clear()
        self.faded.clear()

    def reject(self) -> None:
        self.release_all()
        super().reject()
