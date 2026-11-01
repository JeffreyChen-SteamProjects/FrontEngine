"""
The window frame's own pieces: the brand mark and the command-search entry.

Both paint their icons from the design tokens of the current theme and redraw
them when the palette changes, like the sidebar does.
"""
from __future__ import annotations

from PySide6.QtCore import QEvent, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPalette, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from frontengine.ui.style.nav_icons import pixmap
from frontengine.ui.style.tokens import palette_for

SHORTCUT_HINT = "Ctrl+K"


def _tone(widget: QWidget) -> str:
    return "dark" if widget.palette().color(QPalette.ColorRole.Window).lightness() < 128 else "light"


def brand_pixmap(tone: str, size: int = 26, ratio: float = 2.0) -> QPixmap:
    """An orange tile with an ink paw: the INKSIDE accent and ink, as a small app mark."""
    colors = palette_for(tone)
    side = round(size * ratio)
    image = QImage(side, side, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(colors["accent"]))
    painter.drawRoundedRect(QRectF(0, 0, side, side), side * 0.28, side * 0.28)
    paw = pixmap("pet", colors["on_accent"], size, ratio).toImage()
    inset = side * 0.16
    painter.drawImage(QRectF(inset, inset, side - 2 * inset, side - 2 * inset), paw)
    painter.end()
    result = QPixmap.fromImage(image)
    result.setDevicePixelRatio(ratio)
    return result


class BrandMark(QWidget):
    """App mark and name at the top of the sidebar."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("brandMark")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 6, 4)
        layout.setSpacing(10)
        self.mark = QLabel()
        self.mark.setFixedSize(26, 26)
        self.name = QLabel("FrontEngine")
        self.name.setObjectName("appBrand")
        layout.addWidget(self.mark)
        layout.addWidget(self.name, 1)
        self._refresh()

    def _refresh(self) -> None:
        self.mark.setPixmap(brand_pixmap(_tone(self)))

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.PaletteChange:
            self._refresh()


class CommandSearchButton(QPushButton):
    """A search field look-alike that opens the command palette: icon, caption and shortcut hint."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("commandSearch")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(8)
        self.glass = QLabel()
        self.caption = QLabel()
        self.caption.setObjectName("commandSearchCaption")
        self.hint = QLabel(SHORTCUT_HINT)
        self.hint.setObjectName("shortcutHint")
        for label in (self.glass, self.caption, self.hint):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hint.setFixedHeight(20)
        layout.addWidget(self.glass)
        layout.addWidget(self.caption, 1)
        layout.addWidget(self.hint, 0, Qt.AlignmentFlag.AlignVCenter)
        self.setMinimumHeight(36)
        self._refresh()

    def _refresh(self) -> None:
        self.glass.setPixmap(pixmap("search", palette_for(_tone(self))["muted"], 16))

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.PaletteChange:
            self._refresh()
