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
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QStyle

from frontengine.utils.multi_language.retranslate import retranslator, translate

SIDEBAR_WIDTH = 208

# 群組標題與分頁列用 UserRole 區分，樣式與點擊行為都看這個值。
# Group headings and page rows are told apart by this UserRole value, which
# drives both styling and what a click does.
ROLE_KIND = Qt.ItemDataRole.UserRole
ROLE_PAGE_INDEX = Qt.ItemDataRole.UserRole + 1
# 穩定頁面 ID：之後插入新分頁時，堆疊索引會位移，ID 不會。
# Stable page ID: stack indices shift when a page is inserted, IDs do not.
ROLE_PAGE_ID = Qt.ItemDataRole.UserRole + 2
ROLE_GROUP = Qt.ItemDataRole.UserRole + 3     # the group key a page row belongs to
KIND_GROUP = "group"
KIND_PAGE = "page"


class NavigationSidebar(QListWidget):
    """分組的分頁清單，選到某一頁時送出 page_requested。"""

    page_requested = Signal(int)
    collapsed_changed = Signal(list)       # group keys that are folded, for persistence

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
        self._group: Optional[str] = None
        self._collapsed: set = set()
        self.currentItemChanged.connect(self._on_current_item_changed)
        self.itemClicked.connect(self._toggle_if_group)
        self.itemActivated.connect(self._toggle_if_group)
        retranslator.bind_call(self._retranslate)

    def add_group(self, title_key: str, fallback: str = "") -> QListWidgetItem:
        """加一列群組標題。標題不能被選取；點它會收合或展開該組。
        A group heading: never selected; clicking it folds or unfolds the group."""
        item = QListWidgetItem(translate(title_key, fallback))
        item.setData(ROLE_KIND, KIND_GROUP)
        item.setData(ROLE_GROUP, title_key)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        self._group = title_key
        self._set_arrow(item, False)
        item.setSizeHint(QSize(SIDEBAR_WIDTH, 34))
        self.addItem(item)
        self._labels.append((item, title_key, fallback))
        return item

    def add_page(self, title_key: str, page_index: int, fallback: str = "",
                 page_id: Optional[str] = None) -> QListWidgetItem:
        """加一列分頁。page_index 對應 QStackedWidget 裡的索引；page_id 預設為語言鍵。"""
        item = QListWidgetItem(translate(title_key, fallback))
        item.setData(ROLE_KIND, KIND_PAGE)
        item.setToolTip(item.text())
        item.setData(ROLE_PAGE_INDEX, page_index)
        item.setData(ROLE_PAGE_ID, page_id or title_key)
        item.setData(ROLE_GROUP, self._group)
        item.setSizeHint(QSize(SIDEBAR_WIDTH, 35))
        self.addItem(item)
        self._labels.append((item, title_key, fallback))
        return item

    def select_page(self, page_index: int) -> bool:
        """選取對應某個堆疊索引的那一列；找不到就回傳 False。"""
        for row in range(self.count()):
            item = self.item(row)
            if item.data(ROLE_KIND) == KIND_PAGE and item.data(ROLE_PAGE_INDEX) == page_index:
                if item.isHidden():
                    self.set_group_collapsed(item.data(ROLE_GROUP), False)
                self.setCurrentItem(item)
                return True
        return False

    # ----- folding groups ---------------------------------------------------------------

    def _set_arrow(self, item: QListWidgetItem, collapsed: bool) -> None:
        arrow = QStyle.StandardPixmap.SP_ArrowRight if collapsed else QStyle.StandardPixmap.SP_ArrowDown
        item.setIcon(self.style().standardIcon(arrow))

    def _toggle_if_group(self, item: QListWidgetItem) -> None:
        if item is not None and item.data(ROLE_KIND) == KIND_GROUP:
            key = item.data(ROLE_GROUP)
            self.set_group_collapsed(key, key not in self._collapsed)
            self.collapsed_changed.emit(sorted(self._collapsed))

    def collapsed_groups(self) -> List[str]:
        return sorted(self._collapsed)

    def set_group_collapsed(self, key: str, collapsed: bool) -> None:
        """Hide or show a group's pages; the current page is never hidden away."""
        if collapsed:
            current = self.currentItem()
            if current is not None and current.data(ROLE_GROUP) == key:
                return
            self._collapsed.add(key)
        else:
            self._collapsed.discard(key)
        for row in range(self.count()):
            item = self.item(row)
            if item.data(ROLE_GROUP) != key:
                continue
            if item.data(ROLE_KIND) == KIND_GROUP:
                self._set_arrow(item, collapsed)
            else:
                item.setHidden(collapsed)

    def page_index(self, page_id: str) -> Optional[int]:
        """The current stack index of a stable page ID, or None."""
        for row in range(self.count()):
            item = self.item(row)
            if item.data(ROLE_KIND) == KIND_PAGE and item.data(ROLE_PAGE_ID) == page_id:
                return item.data(ROLE_PAGE_INDEX)
        return None

    def select_page_id(self, page_id: str) -> bool:
        """Select a page by its stable ID rather than its position."""
        index = self.page_index(page_id)
        return index is not None and self.select_page(index)

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
                item.setToolTip(item.text())
            except RuntimeError:  # pragma: no cover - 底層物件已消失
                continue
