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
    QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLayout, QLineEdit,
    QPlainTextEdit, QScrollArea, QSizePolicy, QSlider, QTextEdit, QVBoxLayout, QWidget,
)

from frontengine.utils.multi_language.retranslate import tr

# 控制項不再跟著視窗無限變寬。滑桿橫跨 1900px 沒有任何好處，只是讓一格一格的
# 值更難對準。
# Controls stop growing here. A slider spanning 1900px buys nothing and makes
# every individual value harder to hit.
CONTROL_MAX_WIDTH = 460

# 會被拉寬的控制項也要有下限。第 2 欄吸收多餘寬度之後，滑桿與下拉選單只會拿到
# 自己的 sizeHint——滑桿縮到 85px 就沒辦法好好調了。
# Controls that should be wide need a floor too. With column 2 absorbing the
# slack, sliders and comboboxes fall back to their size hint; a slider 85px wide
# is not something you can aim with.
CONTROL_MIN_WIDTH = 260
_WIDE_CONTROLS = (QComboBox, QSlider, QLineEdit, QPlainTextEdit, QTextEdit)

# 標籤欄的最小寬度，讓同一分區的控制項左邊對齊成一直線。德文與俄文的詞比英文
# 長不少，所以留得比英文所需再寬一些。
# Minimum label column width so controls in a section line up. German and
# Russian words run longer than the English ones, hence the headroom.
LABEL_MIN_WIDTH = 148

PAGE_MARGINS = (28, 22, 28, 0)
FOOTER_MARGINS = (28, 14, 28, 18)
ROW_SPACING = 10
SECTION_SPACING = 22


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
        self._column_layout = QVBoxLayout(self)
        self._column_layout.setContentsMargins(0, 0, 0, 0)
        self._column_layout.setSpacing(ROW_SPACING)

        # 標題也可以是分頁已經有的標籤。像護眼頁那種「一個功能一組設定」的頁面，
        # 功能名稱本來就翻譯好了，拿來當分區標題就不必再開新的語言鍵。
        # The title can be a label the page already has. On pages built as one
        # feature per group - eye care, say - the feature name is already
        # translated, so reusing it needs no new language key.
        self.title_label = title if isinstance(title, QLabel) else tr(QLabel(), title, fallback)
        self.title_label.setObjectName("sectionHeader")
        self._column_layout.addWidget(self.title_label)

        self._grid = QGridLayout()
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(14)
        self._grid.setVerticalSpacing(ROW_SPACING)
        # 第 2 欄吸收多餘寬度，控制項自己有最大寬度，所以吸收的是留白而不是控制項。
        # Column 2 takes the slack; controls have their own maximum, so what
        # grows is the empty space and not the control.
        self._grid.setColumnStretch(2, 1)
        self._column_layout.addLayout(self._grid)
        self._row = 0

    def add_row(self, label: "str | QLabel", control: QWidget, fallback: str = "") -> QWidget:
        """一列：左邊標籤、右邊控制項。"""
        self._grid.addWidget(_form_label(label, fallback), self._row, 0)
        self._grid.addWidget(_cap_width(control), self._row, 1)
        self._row += 1
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
        self._grid.addWidget(_form_label(label, fallback), self._row, 0)
        self._grid.addWidget(_cap_width(slider), self._row, 1)
        value_label.setMinimumWidth(40)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._grid.addWidget(value_label, self._row, 2, Qt.AlignmentFlag.AlignLeft)
        self._row += 1
        return slider

    def add_widget(self, widget: QWidget, label: "str | QLabel | None" = None, fallback: str = "") -> QWidget:
        """
        佔滿整列的控制項（文字編輯區、清單之類）。給了 label_key 就在上面加一行標籤。
        A control that needs the full row (a text area, a list). With a
        ``label_key`` a caption is placed above it.
        """
        if label is not None:
            self._grid.addWidget(_form_label(label, fallback), self._row, 0, 1, 3)
            self._row += 1
        # 單行輸入框即使佔滿整列也還是要有上限：拉到八百多像素只是和同一頁的其他
        # 控制項對不齊，並沒有比較好填。
        # A single-line input keeps its ceiling even across the full row: at 850px
        # it is no easier to fill, just out of line with everything else.
        if isinstance(widget, QLineEdit):
            _cap_width(widget)
        self._grid.addWidget(widget, self._row, 0, 1, 3)
        self._row += 1
        return widget

    def add_inline(self, *widgets: QWidget) -> QWidget:
        """把數個小控制項（勾選框、按鈕）排成同一列。"""
        holder = QWidget()
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(16)
        for widget in widgets:
            row.addWidget(widget)
        row.addStretch(1)
        self._grid.addWidget(holder, self._row, 0, 1, 3)
        self._row += 1
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
        self._grid.addWidget(holder, self._row, 0, 1, 3)
        self._row += 1
        return holder

    def add_layout(self, layout: QLayout) -> QLayout:
        """讓分頁塞進自己組好的版面，過渡期用。"""
        self._grid.addLayout(layout, self._row, 0, 1, 3)
        self._row += 1
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
                 title_fallback: str = "", subtitle_fallback: str = ""):
        super().__init__()
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

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        body = QWidget()
        self._body_layout = QVBoxLayout(body)
        self._body_layout.setContentsMargins(PAGE_MARGINS[0], 4, PAGE_MARGINS[2], 20)
        self._body_layout.setSpacing(SECTION_SPACING)
        self._scroll.setWidget(body)
        self._page_layout.addWidget(self._scroll, 1)

        self._footer: Optional[QWidget] = None

    def add_section(self, title: "str | QLabel", fallback: str = "") -> Section:
        """加一個分區並回傳它，欄位往回傳的物件上加。標題可傳語言鍵或現成標籤。"""
        section = Section(title, fallback)
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
