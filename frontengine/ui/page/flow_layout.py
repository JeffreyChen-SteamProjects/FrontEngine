"""Wrap small groups of controls while preserving their keyboard order."""
from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLabel, QLayout, QLayoutItem, QWidget


class FlowLayout(QLayout):
    """Lay controls out at their natural size, moving overflow to the next line."""

    def __init__(self, parent: QWidget | None = None, spacing: int = 16, *, centred: bool = False) -> None:
        self._items: list[QLayoutItem] = []
        self._centred = centred         # centre each control in its row: a switch beside taller buttons
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(spacing)

    def __del__(self) -> None:
        while self.takeAt(0) is not None:
            pass

    def addItem(self, item: QLayoutItem) -> None:
        """Keep layout items in insertion and keyboard-navigation order."""
        self._items.append(item)

    def count(self) -> int:
        """Return the number of owned items, including during Qt teardown."""
        return len(getattr(self, "_items", ()))

    def itemAt(self, index: int) -> QLayoutItem | None:
        """Return an item without transferring ownership."""
        items = getattr(self, "_items", ())
        return items[index] if 0 <= index < len(items) else None

    def takeAt(self, index: int) -> QLayoutItem | None:
        """Remove an item and transfer its ownership to the caller."""
        items = getattr(self, "_items", [])
        return items.pop(index) if 0 <= index < len(items) else None

    def expandingDirections(self) -> Qt.Orientation:
        """Keep controls at their natural sizes rather than stretching them."""
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        """Tell Qt that wrapping changes this layout's height."""
        return True

    def heightForWidth(self, width: int) -> int:
        """Measure wrapped rows without changing any widget geometry."""
        return self._arrange(QRect(0, 0, width, 0), measure_only=True)

    def setGeometry(self, rect: QRect) -> None:
        """Place visible controls in rows inside the available rectangle."""
        super().setGeometry(rect)
        self._arrange(rect)

    def sizeHint(self) -> QSize:
        """Allow the containing page to shrink to the widest single control."""
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        """Keep each visible control usable and include layout margins."""
        size = QSize(0, 0)
        for item in self._items:
            if not item.isEmpty():
                size = size.expandedTo(item.minimumSize())
        left, top, right, bottom = self.getContentsMargins()
        return size + QSize(left + right, top + bottom)

    def _arrange(self, rect: QRect, measure_only: bool = False) -> int:
        left, top, right, bottom = self.getContentsMargins()
        area = rect.adjusted(left, top, -right, -bottom)
        x, y, line_height = area.x(), area.y(), 0
        row: list[tuple[QLayoutItem, QRect]] = []
        for item in self._items:
            if item.isEmpty():
                continue
            size = item.sizeHint().expandedTo(item.minimumSize())
            if item.hasHeightForWidth():
                size.setWidth(max(size.width(), self._one_line(item)))
                size.setWidth(max(item.minimumSize().width(), min(size.width(), area.width())))
                size.setHeight(max(item.minimumSize().height(), item.heightForWidth(size.width())))
            if x > area.x() and x + size.width() > area.x() + area.width():
                if not measure_only:
                    self._place(row, line_height)
                row = []
                x = area.x()
                y += line_height + self.spacing()
                line_height = 0
            row.append((item, QRect(QPoint(x, y), size)))
            x += size.width() + self.spacing()
            line_height = max(line_height, size.height())
        if not measure_only:
            self._place(row, line_height)
        return y + line_height - rect.y() + bottom

    @staticmethod
    def _one_line(item: QLayoutItem) -> int:
        """A wrapping caption's width on one line; its own size hint wraps it to a block even
        where the row has room."""
        label = item.widget()
        if not isinstance(label, QLabel) or not label.wordWrap():
            return 0
        metrics = label.fontMetrics()
        widest = max((metrics.horizontalAdvance(line) for line in label.text().splitlines()), default=0)
        margins = label.contentsMargins()
        return widest + margins.left() + margins.right() + 2 * (label.margin() + max(0, label.indent())) + 4

    def _place(self, row: list[tuple[QLayoutItem, QRect]], height: int) -> None:
        for item, rect in row:
            if self._centred:
                rect.translate(0, (height - rect.height()) // 2)
            item.setGeometry(rect)
