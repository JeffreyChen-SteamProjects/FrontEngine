"""
挑一個視窗，開一個顯示它即時畫面的小視窗。

和「釘選視窗」的差別在於原視窗動不動：釘選會把它搬到最上層，複本讓它留在原地。
Pick a window and open a small one showing it live. The difference from pinning
is whether the original moves: pinning brings it to the top, a replica leaves it
where it is.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QGridLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QSlider, QWidget,
)

from frontengine.show.replica.replica_widget import WindowReplicaWidget
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import retranslator, tr
from frontengine.utils.window_pin import window_pin
from frontengine.utils.window_replica.dwm_thumbnail import available

# 要顯示來源的哪一塊，用比例（左, 上, 右, 下）表示。
# 用比例而不是像素：來源視窗被調整大小之後，框到的還是同一塊。
# Which part of the source to show, as (left, top, right, bottom) fractions.
# Fractions rather than pixels, so a resize of the source keeps the same part.
CROP_REGIONS = (
    ("window_replica_whole", "Whole window", None),
    ("window_replica_top_half", "Top half", (0.0, 0.0, 1.0, 0.5)),
    ("window_replica_bottom_half", "Bottom half", (0.0, 0.5, 1.0, 1.0)),
    ("window_replica_left_half", "Left half", (0.0, 0.0, 0.5, 1.0)),
    ("window_replica_right_half", "Right half", (0.5, 0.0, 1.0, 1.0)),
    ("window_replica_centre", "Centre", (0.25, 0.25, 0.75, 0.75)),
)


def _t(key: str, fallback: str) -> str:
    return language_wrapper.language_word_dict.get(key, fallback)


class WindowReplicaDialog(QDialog):
    """列出目前的視窗，讓使用者挑一個做成即時複本。"""

    def __init__(self, parent: Optional[QWidget] = None, lister=None,
                 replica_factory=WindowReplicaWidget) -> None:
        front_engine_logger.info("[WindowReplicaDialog] Init")
        super().__init__(parent)
        self.setWindowTitle(_t("window_replica_title", "Replicate a window"))
        self._lister = lister or window_pin.list_windows
        self._replica_factory = replica_factory
        self.replica_widget_list: List[WindowReplicaWidget] = []

        self.window_list = QListWidget()
        self.window_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.refresh_button = tr(QPushButton(), "window_replica_refresh", "Refresh")
        self.refresh_button.clicked.connect(self.reload_windows)
        self.show_button = tr(QPushButton(), "window_replica_show", "Show replica")
        self.show_button.clicked.connect(self.start_replica)

        self.crop_label = tr(QLabel(), "window_replica_region", "Show")
        self.crop_combobox = QComboBox()
        for key, fallback, region in CROP_REGIONS:
            self.crop_combobox.addItem(_t(key, fallback), region)

        self.opacity_label = tr(QLabel(), "window_replica_opacity", "Opacity")
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setValue(100)

        hint_key, hint_fallback = (
            ("window_replica_hint",
             "A second window showing the chosen one live; the original stays where it "
             "is. Drag the replica to move it, double-click it to close it. Windows only.")
            if available() else
            ("window_replica_unsupported", "Window replicas are Windows only."))
        self.hint_label = QLabel(_t(hint_key, hint_fallback))
        retranslator.bind(self.hint_label, hint_key, hint_fallback)
        self.hint_label.setWordWrap(True)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.rejected.connect(self.reject)

        layout = QGridLayout(self)
        layout.addWidget(self.window_list, 0, 0, 1, 2)
        layout.addWidget(self.refresh_button, 1, 0)
        layout.addWidget(self.show_button, 1, 1)
        layout.addWidget(self.crop_label, 2, 0)
        layout.addWidget(self.crop_combobox, 2, 1)
        layout.addWidget(self.opacity_label, 3, 0)
        layout.addWidget(self.opacity_slider, 3, 1)
        layout.addWidget(self.hint_label, 4, 0, 1, 2)
        layout.addWidget(self.button_box, 5, 0, 1, 2)

        self.show_button.setEnabled(available())
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

    def selected(self) -> Optional[Tuple[int, str]]:
        """目前選到的 (handle, 標題)；沒選就是 None。"""
        item = self.window_list.currentItem()
        if item is None:
            return None
        return int(item.data(Qt.ItemDataRole.UserRole)), item.text()

    def start_replica(self) -> Optional[WindowReplicaWidget]:
        """
        對選到的視窗開一個複本。接不上就把它收掉再回 None——留一個永遠黑著的
        小視窗在畫面上，比什麼都不做更糟。
        Open a replica of the selected window. If it cannot attach, the widget is
        closed and this returns None: leaving a permanently black window on
        screen is worse than doing nothing.
        """
        chosen = self.selected()
        if chosen is None:
            return None
        handle, title = chosen
        replica = self._replica_factory(handle, title, self.opacity_slider.value(), None,
                                        self.crop_combobox.currentData())
        if not replica.start():
            front_engine_logger.info(f"[WindowReplicaDialog] could not replicate {title!r}")
            replica.close()
            return None
        self.replica_widget_list.append(replica)
        return replica

    def close_all(self) -> None:
        """關掉這個對話框開過的所有複本。"""
        for replica in list(self.replica_widget_list):
            try:
                replica.close()
            except RuntimeError:  # pragma: no cover - 底層物件已消失
                pass
        self.replica_widget_list.clear()
