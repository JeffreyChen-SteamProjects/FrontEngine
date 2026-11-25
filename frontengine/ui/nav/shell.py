"""
The window frame's own pieces: the brand mark, the command-search entry and the
navigation panel that holds them with the sidebar; and the overlay status bar.

They paint their icons from the design tokens of the current theme and redraw
them when the palette changes, like the sidebar does. The panel folds to a rail
of icons - by its button, Ctrl+B, or by itself while the window is narrow.
"""
from __future__ import annotations

from PySide6.QtCore import QEvent, QRectF, QSize, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from frontengine.ui.nav.sidebar import RAIL_WIDTH, SIDEBAR_WIDTH, NavigationSidebar
from frontengine.ui.style.glass import colors_of, paint_panel, tone_of as _tone
from frontengine.ui.style.nav_icons import pixmap
from frontengine.ui.style.tokens import SHADOW_DEPTH, palette_for
from frontengine.utils.multi_language.retranslate import retranslator, translate

SHORTCUT_HINT = "Ctrl+K"
FOLD_SHORTCUT = "Ctrl+B"
NARROW_WINDOW = 860         # below this window width the panel folds by itself
OUTER = 12                  # between the window's edge and the panel
EDGE = 8                    # between the panel's edge and what is on it
PANEL_WIDTH = SIDEBAR_WIDTH + 2 * EDGE + OUTER
RAIL_PANEL_WIDTH = RAIL_WIDTH + 2 * EDGE + OUTER


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
        self.mark.setFixedSize(30, 30)
        self.name = QLabel("FrontEngine")
        self.name.setObjectName("appBrand")
        layout.addWidget(self.mark)
        layout.addWidget(self.name, 1)
        self._refresh()

    def _refresh(self) -> None:
        self.mark.setPixmap(brand_pixmap(_tone(self), 30))

    def set_compact(self, compact: bool) -> None:
        self.name.setVisible(not compact)

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

    def set_compact(self, compact: bool) -> None:
        for label in (self.caption, self.hint):
            label.setVisible(not compact)
        self.layout().setContentsMargins(14 if compact else 13, 0, 10, 0)

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.PaletteChange:
            self._refresh()


class FoldButton(QPushButton):
    """Folds and opens the navigation panel."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("foldButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(34)
        self._compact = False
        self._caption = QLabel()
        self._caption.setObjectName("foldCaption")
        self._arrow = QLabel()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(8)
        for label in (self._arrow, self._caption):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self._arrow)
        layout.addWidget(self._caption, 1)
        retranslator.bind_call(self._retranslate)
        self.set_compact(False)

    def set_compact(self, compact: bool) -> None:
        self._compact = compact
        key, fallback = ("nav_unfold", "Open the sidebar") if compact else ("nav_fold", "Fold the sidebar")
        self._text = (key, fallback)
        self._caption.setVisible(not compact)
        self._retranslate()
        self.layout().setContentsMargins(14 if compact else 13, 0, 10, 0)
        self._refresh()

    def _retranslate(self) -> None:
        """The tool tip carries the shortcut, so the caption has the panel's width to itself."""
        text = translate(*self._text)
        self._caption.setText(text)
        self.setAccessibleName(text)
        self.setToolTip(f"{text} ({FOLD_SHORTCUT})")

    def _refresh(self) -> None:
        name = "chevron-right" if self._compact else "chevron-left"
        self._arrow.setPixmap(pixmap(name, palette_for(_tone(self))["muted"], 16))

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.PaletteChange:
            self._refresh()


class NavigationPanel(QWidget):
    """A floating glass panel: brand, command search, the pages and the fold button."""

    compact_changed = Signal(bool)      # the user's own choice, for persistence

    def __init__(self, sidebar: NavigationSidebar, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("navigationPanel")
        self.sidebar = sidebar
        self.brand = BrandMark()
        self.search = CommandSearchButton()
        self.fold_button = FoldButton()
        self.fold_button.clicked.connect(self.toggle)
        self._chosen = False            # folded by the user
        self._narrow = False            # the window leaves no room
        self._opened_narrow = False     # opened by hand although it is narrow
        layout = QVBoxLayout(self)
        layout.setContentsMargins(OUTER + EDGE, 18, EDGE, 24)
        layout.setSpacing(10)
        layout.addWidget(self.brand)
        layout.addWidget(self.search)
        layout.addWidget(sidebar, 1)
        layout.addWidget(self.fold_button)
        self._apply()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        paint_panel(painter, QRectF(self.rect()).adjusted(OUTER, 4, 0, -2), colors_of(self))

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.PaletteChange:
            self.update()

    @property
    def compact(self) -> bool:
        return self.sidebar.compact

    def sizeHint(self) -> QSize:
        return QSize(RAIL_PANEL_WIDTH if self.compact else PANEL_WIDTH, super().sizeHint().height())

    def set_chosen(self, compact: bool) -> None:
        """The stored choice, applied without reporting it back."""
        self._chosen = bool(compact)
        self._apply()

    def set_window_width(self, width: int) -> None:
        """Fold while the window is narrow and open again when it widens."""
        narrow = width < NARROW_WINDOW
        if narrow != self._narrow:
            self._narrow, self._opened_narrow = narrow, False
            self._apply()

    def toggle(self) -> None:
        if self._narrow:
            self._opened_narrow = self.compact
        else:
            self._chosen = not self.compact
            self.compact_changed.emit(self._chosen)
        self._apply()

    def _apply(self) -> None:
        compact = not self._opened_narrow if self._narrow else self._chosen
        self.sidebar.set_compact(compact)
        # At least a rail, whatever is showing: the open panel must not hold the window wide, or it
        # could never be made narrow enough to fold the panel.
        self.setMinimumWidth(RAIL_PANEL_WIDTH)
        self.setMaximumWidth(RAIL_PANEL_WIDTH if compact else PANEL_WIDTH)
        self.updateGeometry()
        for part in (self.brand, self.search, self.fold_button):
            part.set_compact(compact)


class OverlayStatusBar(QWidget):
    """What is on screen right now, and the two things to do about it, on every page."""

    toggle_requested = Signal(bool)          # True: hide every overlay; False: show them again
    close_requested = Signal()

    POLL_MS = 1000

    def __init__(self, overlays, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("overlayStatus")
        self._overlays = overlays            # returns the live overlays, asked again every time
        self.visible_count, self.hidden_count = 0, 0
        self.text = QLabel()
        self.text.setObjectName("statusText")
        self.toggle_button, self.close_button = QPushButton(), QPushButton()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 5, 10, 5 + SHADOW_DEPTH)
        layout.setSpacing(4)
        layout.addWidget(self.text, 1)
        for button in (self.toggle_button, self.close_button):
            button.setObjectName("statusAction")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(button)
        self.toggle_button.clicked.connect(lambda: self.toggle_requested.emit(self.visible_count > 0))
        self.close_button.clicked.connect(self.close_requested.emit)
        retranslator.bind(self.close_button, "control_center_close_all", "Close all")
        self._timer = QTimer(self)
        self._timer.setInterval(self.POLL_MS)
        self._timer.timeout.connect(self.refresh)
        retranslator.bind_call(self._retranslate)
        self._retranslate()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh()
        self._timer.start()

    def hideEvent(self, event) -> None:
        self._timer.stop()
        super().hideEvent(event)

    def refresh(self) -> None:
        """Count the overlays again and relabel only when something changed."""
        visible = hidden = 0
        seen = set()
        for overlay in self._overlays():
            if id(overlay) in seen:
                continue
            seen.add(id(overlay))
            try:
                if overlay.isVisible():
                    visible += 1
                else:
                    hidden += 1
            except (RuntimeError, AttributeError):       # closed, or not a widget
                continue
        if (visible, hidden) != (self.visible_count, self.hidden_count):
            self.visible_count, self.hidden_count = visible, hidden
            self._retranslate()

    def _retranslate(self) -> None:
        if self.visible_count:
            text = translate("overlay_status_visible", "Overlays on screen: {count}").format(count=self.visible_count)
        elif self.hidden_count:
            text = translate("overlay_status_hidden", "Overlays hidden: {count}").format(count=self.hidden_count)
        else:
            text = translate("overlay_status_none", "Nothing on screen")
        self.text.setText(text)
        key, fallback = ("control_center_hide_all", "Hide all") if self.visible_count or not self.hidden_count \
            else ("control_center_show_all", "Show all")
        self.toggle_button.setText(translate(key, fallback))
        for button in (self.toggle_button, self.close_button):
            button.setEnabled(bool(self.visible_count or self.hidden_count))

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        paint_panel(painter, QRectF(self.rect()), colors_of(self), radius=17)
