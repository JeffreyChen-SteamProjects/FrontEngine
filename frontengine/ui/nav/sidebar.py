"""
左側導覽：分組的分頁清單。

先前十六個分頁擠在一排，視窗一窄就出現捲動箭頭，而且十六個並排的詞看不出誰跟
誰是一類的。改成側邊欄之後：永遠不會溢出、目前在哪一頁隨時看得到、之後再加功
能也只是清單多一列。

清單項目不是 QWidget，沒辦法交給 retranslator 的 bind() 用弱參考持有，所以改用
bind_call() 這個逃生口——換語言時整份重寫一次。

The left-hand navigation: the pages as a grouped list on a glass panel.

Sixteen tabs in one row grew scroll arrows as soon as the window narrowed, and
sixteen words side by side gave no clue which belonged together. As a sidebar it
cannot overflow, the current page is always visible, and a new feature later is
one more line in a list.

List items are not QWidgets, so the retranslator cannot hold them weakly through
bind(); this uses the bind_call() escape hatch and rewrites the lot on a
language change.

Rows are painted by their own delegate: the selected page is a solid pill.
``set_compact`` folds the list to a rail of icons.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtCore import QEvent, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QStyle, QStyledItemDelegate

from frontengine.ui.style.glass import tone_of
from frontengine.ui.style.nav_icons import ICON_SIZE, icon
from frontengine.ui.style.tokens import palette_for
from frontengine.utils.multi_language.retranslate import retranslator, translate

SIDEBAR_WIDTH = 196
RAIL_WIDTH = 46                        # folded: icons only
ROW_HEIGHT, GROUP_HEIGHT, RAIL_GROUP_HEIGHT = 36, 30, 14

# 群組標題與分頁列用 UserRole 區分，樣式與點擊行為都看這個值。
# Group headings and page rows are told apart by this UserRole value, which
# drives both styling and what a click does.
ROLE_KIND = Qt.ItemDataRole.UserRole
ROLE_PAGE_INDEX = Qt.ItemDataRole.UserRole + 1
# 穩定頁面 ID：之後插入新分頁時，堆疊索引會位移，ID 不會。
# Stable page ID: stack indices shift when a page is inserted, IDs do not.
ROLE_PAGE_ID = Qt.ItemDataRole.UserRole + 2
ROLE_GROUP = Qt.ItemDataRole.UserRole + 3     # the group key a page row belongs to
ROLE_ICON = Qt.ItemDataRole.UserRole + 4      # nav_icons name of a page row
KIND_GROUP = "group"
KIND_PAGE = "page"


class NavigationDelegate(QStyledItemDelegate):
    """Draws the list: quiet group captions, pages with the selected one on a pill, and the rail."""

    def paint(self, painter: QPainter, option, index) -> None:
        sidebar = self.parent()
        colors = palette_for(tone_of(sidebar))
        painter.save()
        painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        if index.data(ROLE_KIND) == KIND_GROUP:
            self._paint_group(painter, option, index, colors, sidebar.compact)
        else:
            self._paint_page(painter, option, index, colors, sidebar.compact)
        painter.restore()

    @staticmethod
    def _text(painter, rect: QRect, text: str) -> None:
        painter.drawText(rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                         painter.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, rect.width()))

    def _paint_group(self, painter, option, index, colors, compact: bool) -> None:
        if compact:
            middle = QRectF(option.rect).center()
            painter.setPen(QPen(QColor(colors["well_edge"]), 1.5))
            painter.drawLine(int(middle.x()) - 9, int(middle.y()), int(middle.x()) + 9, int(middle.y()))
            return
        font = QFont(option.font)
        font.setPixelSize(11)
        painter.setFont(font)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        painter.setPen(QColor(colors["text" if hovered else "muted"]))
        self._text(painter, QRect(option.rect).adjusted(14, 8, -30, 0), index.data(Qt.ItemDataRole.DisplayRole))
        chevron = index.data(Qt.ItemDataRole.DecorationRole)
        if chevron is not None:
            chevron.paint(painter, QRect(option.rect.right() - 28, option.rect.center().y() - 3, 14, 14))

    def _paint_page(self, painter, option, index, colors, compact: bool) -> None:
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        pill = QRectF(option.rect).adjusted(1, 2, -1, -2)
        if selected or hovered:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(colors["pill" if selected else "glass_hover"]))
            painter.drawRoundedRect(pill, pill.height() / 2, pill.height() / 2)
        if option.state & QStyle.StateFlag.State_HasFocus and not selected:
            painter.setPen(QPen(QColor(colors["accent_line"]), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(pill.adjusted(1, 1, -1, -1), pill.height() / 2, pill.height() / 2)
        size = ICON_SIZE.width()
        left = option.rect.center().x() - size // 2 + 1 if compact else option.rect.left() + 14
        mark = index.data(Qt.ItemDataRole.DecorationRole)
        if mark is not None:
            mark.paint(painter, QRect(left, option.rect.center().y() - size // 2 + 1, size, size),
                       Qt.AlignmentFlag.AlignCenter, QIcon.Mode.Selected if selected else QIcon.Mode.Normal)
        if compact:
            return
        font = QFont(option.font)
        font.setWeight(QFont.Weight.DemiBold if selected else QFont.Weight.Normal)
        painter.setFont(font)
        painter.setPen(QColor(colors["on_pill" if selected else "text"]))
        self._text(painter, QRect(option.rect).adjusted(14 + size + 11, 0, -12, 0),
                   index.data(Qt.ItemDataRole.DisplayRole))


class NavigationSidebar(QListWidget):
    """分組的分頁清單，選到某一頁時送出 page_requested。"""

    page_requested = Signal(int)
    collapsed_changed = Signal(list)       # group keys that are folded, for persistence

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("navSidebar")
        self.compact = False
        self.setFixedWidth(SIDEBAR_WIDTH)
        self.setMouseTracking(True)
        self.setItemDelegate(NavigationDelegate(self))
        self.setFrameShape(QListWidget.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        # 分頁列之間不需要虛線焦點框，選取本身已經夠明顯。
        self.setUniformItemSizes(False)
        self.setIconSize(ICON_SIZE)

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
        item = QListWidgetItem(translate(title_key, fallback).upper())
        item.setData(ROLE_KIND, KIND_GROUP)
        item.setData(ROLE_GROUP, title_key)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        self._group = title_key
        self._set_arrow(item, False)
        item.setSizeHint(self._row_size(KIND_GROUP))
        self.addItem(item)
        self._labels.append((item, title_key, fallback))
        return item

    def add_page(self, title_key: str, page_index: int, fallback: str = "",
                 page_id: Optional[str] = None, icon_name: str = "extension") -> QListWidgetItem:
        """加一列分頁。page_index 對應 QStackedWidget 裡的索引；page_id 預設為語言鍵。"""
        item = QListWidgetItem(translate(title_key, fallback))
        item.setData(ROLE_KIND, KIND_PAGE)
        item.setToolTip(item.text())
        item.setData(ROLE_PAGE_INDEX, page_index)
        item.setData(ROLE_PAGE_ID, page_id or title_key)
        item.setData(ROLE_GROUP, self._group)
        item.setData(ROLE_ICON, icon_name)
        item.setIcon(icon(icon_name, *self._icon_colors()))
        item.setSizeHint(self._row_size(KIND_PAGE))
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

    # ----- folding to a rail -------------------------------------------------------------

    def _row_size(self, kind: str) -> QSize:
        width = RAIL_WIDTH if self.compact else SIDEBAR_WIDTH
        if kind == KIND_PAGE:
            return QSize(width, ROW_HEIGHT)
        return QSize(width, RAIL_GROUP_HEIGHT if self.compact else GROUP_HEIGHT)

    def set_compact(self, compact: bool) -> None:
        """Fold to a rail of icons (names stay as tool tips), or open again."""
        if compact == self.compact:
            return
        self.compact = compact
        self.setFixedWidth(RAIL_WIDTH if compact else SIDEBAR_WIDTH)
        for row in range(self.count()):
            item = self.item(row)
            item.setSizeHint(self._row_size(item.data(ROLE_KIND)))
        current = self.currentItem()
        if not compact and current is not None:          # picked on the rail, out of a folded group
            self._collapsed.discard(current.data(ROLE_GROUP))
        self._apply_groups()
        if current is not None:
            self.scrollToItem(current)

    def _apply_groups(self) -> None:
        """Hide the pages of folded groups. The rail shows every page: it has no captions to tell by."""
        for row in range(self.count()):
            item = self.item(row)
            collapsed = item.data(ROLE_GROUP) in self._collapsed
            if item.data(ROLE_KIND) == KIND_GROUP:
                self._set_arrow(item, collapsed)
            else:
                item.setHidden(collapsed and not self.compact)

    # ----- folding groups ---------------------------------------------------------------

    def _icon_colors(self) -> tuple[str, str]:
        """Text colour for rows, the pill's own text colour for the selected one, in the current theme."""
        colors = palette_for(tone_of(self))
        return colors["text"], colors["on_pill"]

    def _set_arrow(self, item: QListWidgetItem, collapsed: bool) -> None:
        """A small chevron in the theme's muted ink (the platform arrows vanish on a dark sidebar)."""
        muted, _text = self._icon_colors()
        item.setIcon(icon("chevron-right" if collapsed else "chevron-down", muted))

    def changeEvent(self, event: QEvent) -> None:
        """A theme change swaps the palette: redraw chevrons and page icons in the new tone."""
        super().changeEvent(event)
        if event.type() == QEvent.Type.PaletteChange:
            colors = self._icon_colors()
            for row in range(self.count()):
                item = self.item(row)
                if item.data(ROLE_KIND) == KIND_GROUP:
                    self._set_arrow(item, item.data(ROLE_GROUP) in self._collapsed)
                else:
                    item.setIcon(icon(item.data(ROLE_ICON) or "extension", *colors))

    def _toggle_if_group(self, item: QListWidgetItem) -> None:
        if item is not None and item.data(ROLE_KIND) == KIND_GROUP and not self.compact:
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
        self._apply_groups()

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
                text = translate(key, fallback)
                item.setText(text.upper() if item.data(ROLE_KIND) == KIND_GROUP else text)
                item.setToolTip(item.text())
            except RuntimeError:  # pragma: no cover - 底層物件已消失
                continue
