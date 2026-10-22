"""
分頁的共用版面元件：頁首、分區、表單列、底部動作列。

以前每個分頁都是自己開一個 `QGridLayout(self)`、把控制項塞進格子座標，邊距設成
0，也沒有任何最大寬度。結果是滑桿會跟著視窗拉到一千多像素寬、標籤貼在視窗最
左邊、所有控制項都在同一個視覺層級——看得到全部，卻看不出哪個重要。

這裡把版面規則收在一個地方：分區有標題、標籤欄對齊、控制項有最大寬度、主要動
作固定在底部而且長得跟次要動作不一樣。分頁只描述「有哪些欄位」，不再自己排版。

Shared layout building blocks for the setting pages: a header, sections, form
rows, and a footer action bar.

Every page used to open its own ``QGridLayout(self)``, drop widgets at raw grid
coordinates, zero the margins and set no maximum width anywhere. Sliders grew to
whatever the window was, labels sat flush against the left edge, and everything
carried the same visual weight - you could see all of it and none of it stood
out.

The rules live here instead: sections carry a title, label columns line up,
controls stop growing at a readable width, and the primary action sits in a
fixed footer looking different from everything else. A page now describes which
fields it has and not how to arrange them.
"""
from __future__ import annotations

from typing import Iterable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFormLayout, QFrame, QGridLayout, QHBoxLayout, QLabel, QLayout, QLineEdit,
    QPlainTextEdit, QPushButton, QScrollArea, QSizePolicy, QSlider, QTextEdit, QToolButton,
    QVBoxLayout, QWidget,
)

from frontengine.utils.multi_language.retranslate import retranslator, tr
from frontengine.ui.page.action_menu import ActionMenu
from frontengine.ui.page.flow_layout import FlowLayout

# 控制項不再跟著視窗無限變寬。滑桿橫跨 1900px 沒有任何好處，只是讓一格一格的
# 值更難對準。
# Controls stop growing here. A slider spanning 1900px buys nothing and makes
# every individual value harder to hit.
CONTROL_MAX_WIDTH = 460

# 保留控制項可操作的最小寬度；空間不足時讓表單換行，而不是把滑桿擠到難以操作。
# Keep controls wide enough to use; wrap form rows when space is short instead
# of squeezing a slider down to an unusable width.
CONTROL_MIN_WIDTH = 260
_WIDE_CONTROLS = (QComboBox, QSlider, QLineEdit, QPlainTextEdit, QTextEdit)

# 標籤欄的最小寬度，讓同一分區的控制項左邊對齊成一直線。德文與俄文的詞比英文
# 長不少，所以留得比英文所需再寬一些。
# Minimum label column width so controls in a section line up. German and
# Russian words run longer than the English ones, hence the headroom.
LABEL_MIN_WIDTH = 148

PAGE_MARGINS = (28, 22, 28, 0)
FOOTER_MARGINS = (28, 14, 28, 18)
ROW_SPACING = 14
SECTION_SPACING = 16


def _form_label(label: "str | QLabel", fallback: str = "") -> QLabel:
    """
    欄位標籤：固定最小寬度讓同一分區的控制項對齊成一直線。

    可以傳語言鍵，也可以傳分頁已經建好的 QLabel——很多分頁本來就把標籤存成屬性
    在別處用，重建一個會讓那些屬性指向畫面上不存在的東西。
    Accepts either a language key or a QLabel the page already built: pages keep
    their labels as attributes and use them elsewhere, so building a second one
    would leave those attributes pointing at something not on screen.
    """
    widget = label if isinstance(label, QLabel) else tr(QLabel(), label, fallback)
    widget.setMinimumWidth(LABEL_MIN_WIDTH)
    widget.setWordWrap(True)
    widget.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    return widget


def _cap_width(widget: QWidget) -> QWidget:
    """
    把控制項的寬度收在可讀範圍內：會被拉寬的那幾類給下限，全部給上限。
    數字框那種本來就短的不給下限，硬拉寬只會看起來很怪。
    Bound a control's width: a floor for the kinds that should be wide, a ceiling
    for everything. Naturally short controls like a spin box get no floor -
    stretching those just looks wrong.
    """
    if isinstance(widget, _WIDE_CONTROLS) and widget.minimumWidth() < CONTROL_MIN_WIDTH:
        widget.setMinimumWidth(CONTROL_MIN_WIDTH)
    if widget.maximumWidth() > CONTROL_MAX_WIDTH:
        widget.setMaximumWidth(CONTROL_MAX_WIDTH)
    return widget


class Section(QWidget):
    """
    一組相關欄位，帶一個小標題。標題用 objectName 上樣式，不在這裡寫死顏色。
    A group of related fields under a small heading. The heading is styled by
    objectName rather than hard-coded colours here.
    """

    def __init__(self, title: "str | QLabel", fallback: str = "",
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("settingSection")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self._column_layout = QVBoxLayout(self)
        self._column_layout.setContentsMargins(20, 18, 20, 20)
        self._column_layout.setSpacing(18)

        # 標題也可以是分頁已經有的標籤。像護眼頁那種「一個功能一組設定」的頁面，
        # 功能名稱本來就翻譯好了，拿來當分區標題就不必再開新的語言鍵。
        # The title can be a label the page already has. On pages built as one
        # feature per group - eye care, say - the feature name is already
        # translated, so reusing it needs no new language key.
        self.title_label = title if isinstance(title, QLabel) else tr(QLabel(), title, fallback)
        self.title_label.setObjectName("sectionHeader")
        heading = QHBoxLayout()
        heading.addWidget(self.title_label)
        heading.addStretch()
        self.toggle_button = QToolButton()
        self.toggle_button.setObjectName("sectionToggle")
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(True)
        self.toggle_button.hide()
        self.toggle_button.toggled.connect(self._set_expanded)
        heading.addWidget(self.toggle_button)
        self._column_layout.addLayout(heading)

        self.content = QWidget()
        self.content.setObjectName("sectionContent")
        self._form = QFormLayout(self.content)
        self._form.setContentsMargins(0, 0, 0, 0)
        self._form.setHorizontalSpacing(14)
        self._form.setVerticalSpacing(ROW_SPACING)
        self._form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self._form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self._form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._column_layout.addWidget(self.content)

    def set_collapsible(self, collapsed: bool = True) -> None:
        """Keep less-used settings available behind an explicit details toggle."""
        self.toggle_button.show()
        self.toggle_button.setChecked(not collapsed)
        self._set_expanded(not collapsed)

    def set_stacked(self) -> None:
        """Place every label above its field in a narrow inspector panel."""
        self._form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

    def _set_expanded(self, expanded: bool) -> None:
        self.content.setVisible(expanded)
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        retranslator.set_text(self.toggle_button, "ui_hide_details" if expanded else "ui_show_details")

    def add_actions(self, *buttons: QPushButton, prominent: int = 1,
                    menu_key: str = "ui_more_actions") -> QWidget:
        """Keep frequent actions visible and put secondary commands in a menu."""
        holder = QWidget()
        holder.setObjectName("inlineActions")
        row = FlowLayout(holder, spacing=10)
        for button in buttons[:prominent]:
            row.addWidget(button)
        if buttons[prominent:]:
            row.addWidget(ActionMenu(buttons[prominent:], menu_key))
        self._form.addRow(holder)
        return holder

    def add_row(self, label: "str | QLabel", control: QWidget, fallback: str = "") -> QWidget:
        """一列：左邊標籤、右邊控制項。"""
        caption = _form_label(label, fallback)
        caption.setBuddy(control)
        self._form.addRow(caption, _cap_width(control))
        return control

    def add_slider_row(self, label: "str | QLabel", slider: QWidget, value_label: QWidget,
                       fallback: str = "") -> QWidget:
        """
        滑桿列：標籤、滑桿、目前值。值放在滑桿右邊而不是左邊——由左讀到右時，
        先看到自己在調什麼，再看到調到多少。
        A slider row: label, slider, current value. The value sits to the right
        of the slider: read left to right you meet what you are changing before
        what it is set to.
        """
        caption = _form_label(label, fallback)
        caption.setBuddy(slider)
        holder = QWidget()
        holder.setObjectName("inlineActions")
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(14)
        row.addWidget(_cap_width(slider), 1)
        value_label.setMinimumWidth(40)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(value_label)
        holder.setMaximumWidth(CONTROL_MAX_WIDTH + 54)
        self._form.addRow(caption, holder)
        return slider

    def add_widget(self, widget: QWidget, label: "str | QLabel | None" = None, fallback: str = "") -> QWidget:
        """
        佔滿整列的控制項（文字編輯區、清單之類）。給了 label_key 就在上面加一行標籤。
        A control that needs the full row (a text area, a list). With a
        ``label_key`` a caption is placed above it.
        """
        if label is not None:
            caption = _form_label(label, fallback)
            caption.setBuddy(widget)
            self._form.addRow(caption)
        # 單行輸入框即使佔滿整列也還是要有上限：拉到八百多像素只是和同一頁的其他
        # 控制項對不齊，並沒有比較好填。
        # A single-line input keeps its ceiling even across the full row: at 850px
        # it is no easier to fill, just out of line with everything else.
        if isinstance(widget, QLineEdit):
            _cap_width(widget)
        self._form.addRow(widget)
        return widget

    def add_inline(self, *widgets: QWidget) -> QWidget:
        """Small controls share a row and wrap when the page is narrow."""
        holder = QWidget()
        holder.setObjectName("inlineActions")
        row = FlowLayout(holder)
        for widget in widgets:
            row.addWidget(widget)
        self._form.addRow(holder)
        return holder

    def add_button_grid(self, *widgets: QWidget, columns: int = 3) -> QWidget:
        """
        一堆同類按鈕排成幾欄的網格。控制中心先前把十九顆按鈕疊成單獨一直行，
        高得看不完；排成三欄之後一眼就看得到全部。
        A pile of same-kind buttons in a few columns. The control centre used to
        stack nineteen buttons in a single column taller than the window; in
        three columns the whole set is visible at once.
        """
        holder = QWidget()
        grid = QGridLayout(holder)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        for index, widget in enumerate(widgets):
            grid.addWidget(widget, index // columns, index % columns)
        for column in range(columns):
            grid.setColumnStretch(column, 1)
        self._form.addRow(holder)
        return holder

    def add_layout(self, layout: QLayout) -> QLayout:
        """讓分頁塞進自己組好的版面，過渡期用。"""
        self._form.addRow(layout)
        return layout


class SettingPage(QWidget):
    """
    分頁骨架：頁首（標題 + 一句說明）、可捲動的內容、底部動作列。

    內容放在捲動區裡，所以視窗縮小時欄位是被捲走而不是被擠扁；底部動作列不在捲
    動區內，「開始」按鈕永遠看得到。

    The page scaffold: a header (title plus one line saying what the page does),
    a scrolling body, and a footer action bar.

    The body scrolls, so shrinking the window scrolls fields out of view instead
    of squashing them, and the footer stays outside that scroll area - the start
    button never leaves the screen.
    """

    def __init__(self, title_key: str, subtitle_key: str = "",
                 title_fallback: str = "", subtitle_fallback: str = "", *, compact: bool = False):
        super().__init__()
        self.setProperty("settingPage", True)
        self._page_layout = QVBoxLayout(self)
        self._page_layout.setContentsMargins(0, 0, 0, 0)
        self._page_layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("pageHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(*PAGE_MARGINS[:2], PAGE_MARGINS[2], 16)
        header_layout.setSpacing(4)

        self.title_label = tr(QLabel(), title_key, title_fallback)
        self.title_label.setObjectName("pageTitle")
        header_layout.addWidget(self.title_label)

        self.subtitle_label: Optional[QLabel] = None
        if subtitle_key:
            self.subtitle_label = tr(QLabel(), subtitle_key, subtitle_fallback)
            self.subtitle_label.setObjectName("pageSubtitle")
            self.subtitle_label.setWordWrap(True)
            header_layout.addWidget(self.subtitle_label)
        self._page_layout.addWidget(header)
        header.setVisible(not compact)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        body = QWidget()
        body.setObjectName("pageContent")
        self._body_layout = QVBoxLayout(body)
        self._body_layout.setContentsMargins(PAGE_MARGINS[0], 4, PAGE_MARGINS[2], 20)
        if compact:
            self._body_layout.setContentsMargins(12, 12, 12, 12)
        self._body_layout.setSpacing(SECTION_SPACING)
        self._scroll.setWidget(body)
        self._page_layout.addWidget(self._scroll, 1)

        self._footer: Optional[QWidget] = None

    def add_section(self, title: "str | QLabel", fallback: str = "", *, collapsed: bool = False) -> Section:
        """加一個分區並回傳它，欄位往回傳的物件上加。標題可傳語言鍵或現成標籤。"""
        section = Section(title, fallback)
        if collapsed:
            section.set_collapsible()
        self._body_layout.addWidget(section)
        return section

    def add_body_widget(self, widget: QWidget, stretch: int = 0) -> QWidget:
        """不屬於任何分區、直接放進內容區的控制項（記錄區之類）。"""
        self._body_layout.addWidget(widget, stretch)
        return widget

    def finish_body(self) -> None:
        """
        內容排完後呼叫：把剩下的空間推到最後，分區才會由上往下堆疊而不是被平均
        拉開。先前那些巨大的空隙就是少了這一步。
        Call once the body is filled: push the slack to the end so sections stack
        from the top instead of being spread apart. The old gaping holes between
        controls were exactly this missing.
        """
        self._body_layout.addStretch(1)

    def set_footer(self, primary: Optional[QWidget] = None,
                   status: Optional[QWidget] = None,
                   extra: Optional[Iterable[QWidget]] = None) -> QWidget:
        """
        底部動作列：狀態文字在左、主要動作在右。主要按鈕掛上 objectName，樣式表
        才能把它跟其他按鈕區分開——先前「選擇檔案」和「開始播放」長得一模一樣。
        The footer: status text on the left, the primary action on the right. The
        primary button carries an objectName so the stylesheet can tell it apart
        from the rest; "choose file" and "start playing" used to look identical.
        """
        footer = QWidget()
        footer.setObjectName("pageFooter")
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(*FOOTER_MARGINS)
        layout.setSpacing(12)

        if status is not None:
            status.setObjectName("pageStatus")
            layout.addWidget(status)
        layout.addStretch(1)
        for widget in extra or ():
            layout.addWidget(widget)
        if primary is not None:
            primary.setObjectName("primaryAction")
            primary.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            layout.addWidget(primary)

        self._page_layout.addWidget(footer)
        self._footer = footer
        return footer
