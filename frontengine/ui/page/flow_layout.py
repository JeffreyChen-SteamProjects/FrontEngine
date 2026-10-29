"""Wrap small groups of controls while preserving their keyboard order."""
from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout, QLayoutItem, QWidget


class FlowLayout(QLayout):
    """Lay controls out at their natural size, moving overflow to the next line."""

    def __init__(self, parent: QWidget | None = None, spacing: int = 16) -> None:
        self._items: list[QLayoutItem] = []
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
        for item in self._items:
            if item.isEmpty():
                continue
            size = item.sizeHint().expandedTo(item.minimumSize())
            if x > area.x() and x + size.width() > area.x() + area.width():
                x = area.x()
                y += line_height + self.spacing()
                line_height = 0
            if not measure_only:
                item.setGeometry(QRect(QPoint(x, y), size))
            x += size.width() + self.spacing()
            line_height = max(line_height, size.height())
        return y + line_height - rect.y() + bottom
