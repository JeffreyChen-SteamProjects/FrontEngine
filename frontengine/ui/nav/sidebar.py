"""
左側導覽：分組的分頁清單。

先前十六個分頁擠在一排，視窗一窄就出現捲動箭頭，而且十六個並排的詞看不出誰跟
誰是一類的。改成側邊欄之後：永遠不會溢出、目前在哪一頁隨時看得到、之後再加功
能也只是清單多一列。

清單項目不是 QWidget，沒辦法交給 retranslator 的 bind() 用弱參考持有，所以改用
bind_call() 這個逃生口——換語言時整份重寫一次。

The left-hand navigation: the pages as a grouped list.

Sixteen tabs in one row grew scroll arrows as soon as the window narrowed, and
sixteen words side by side gave no clue which belonged together. As a sidebar it
cannot overflow, the current page is always visible, and a new feature later is
one more line in a list.

List items are not QWidgets, so the retranslator cannot hold them weakly through
bind(); this uses the bind_call() escape hatch and rewrites the lot on a
language change.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem

from frontengine.utils.multi_language.retranslate import retranslator, translate

SIDEBAR_WIDTH = 208

# 群組標題與分頁列用 UserRole 區分，樣式與點擊行為都看這個值。
# Group headings and page rows are told apart by this UserRole value, which
# drives both styling and what a click does.
ROLE_KIND = Qt.ItemDataRole.UserRole
ROLE_PAGE_INDEX = Qt.ItemDataRole.UserRole + 1
KIND_GROUP = "group"
KIND_PAGE = "page"


class NavigationSidebar(QListWidget):
    """分組的分頁清單，選到某一頁時送出 page_requested。"""

    page_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("navSidebar")
        self.setFixedWidth(SIDEBAR_WIDTH)
        self.setFrameShape(QListWidget.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        # 分頁列之間不需要虛線焦點框，選取本身已經夠明顯。
        self.setUniformItemSizes(False)

        # (item, key, fallback)，換語言時照這張表重寫
        self._labels: List[Tuple[QListWidgetItem, str, str]] = []
        self.currentItemChanged.connect(self._on_current_item_changed)
        retranslator.bind_call(self._retranslate)

    def add_group(self, title_key: str, fallback: str = "") -> QListWidgetItem:
        """加一列群組標題。標題不能被選取，點了也不會換頁。"""
        item = QListWidgetItem(translate(title_key, fallback))
        item.setData(ROLE_KIND, KIND_GROUP)
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        item.setSizeHint(QSize(SIDEBAR_WIDTH, 34))
        self.addItem(item)
        self._labels.append((item, title_key, fallback))
        return item

    def add_page(self, title_key: str, page_index: int, fallback: str = "") -> QListWidgetItem:
        """加一列分頁。page_index 對應 QStackedWidget 裡的索引。"""
        item = QListWidgetItem(translate(title_key, fallback))
        item.setData(ROLE_KIND, KIND_PAGE)
        item.setData(ROLE_PAGE_INDEX, page_index)
        item.setSizeHint(QSize(SIDEBAR_WIDTH, 32))
        self.addItem(item)
        self._labels.append((item, title_key, fallback))
        return item

    def select_page(self, page_index: int) -> bool:
        """選取對應某個堆疊索引的那一列；找不到就回傳 False。"""
        for row in range(self.count()):
            item = self.item(row)
            if item.data(ROLE_KIND) == KIND_PAGE and item.data(ROLE_PAGE_INDEX) == page_index:
                self.setCurrentItem(item)
                return True
        return False

    def page_label(self, page_index: int) -> str:
        """某個堆疊索引目前顯示的文字（測試與記錄用）。"""
        for row in range(self.count()):
            item = self.item(row)
            if item.data(ROLE_KIND) == KIND_PAGE and item.data(ROLE_PAGE_INDEX) == page_index:
                return item.text()
        return ""

    def _on_current_item_changed(self, current: Optional[QListWidgetItem], _previous) -> None:
        if current is None or current.data(ROLE_KIND) != KIND_PAGE:
            return
        index = current.data(ROLE_PAGE_INDEX)
        if isinstance(index, int):
            self.page_requested.emit(index)

    def _retranslate(self) -> None:
        """換語言時把每一列的文字重寫一次。"""
        for item, key, fallback in self._labels:
            try:
                item.setText(translate(key, fallback))
            except RuntimeError:  # pragma: no cover - 底層物件已消失
                continue
