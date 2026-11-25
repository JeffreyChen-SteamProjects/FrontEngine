"""
The drawing layer's own controls: tools, colours, undo, clear and a way out.

The layer covers the whole monitor, the settings window included, so everything
needed while drawing is on the layer itself. It is a child of the layer, drawn in
the same window, and can be dragged aside by its grip.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from frontengine.utils.multi_language.retranslate import retranslator, tr

if TYPE_CHECKING:
    from frontengine.show.presentation.annotation_overlay import AnnotationOverlay

# One look whatever the app theme: it floats over arbitrary screen content. The INKSIDE inks.
INK, PAPER, PAPER_PRESSED, ACCENT, MUTED = "#171715", "#FFFDF6", "#EFE6D2", "#F56A24", "#5E584C"
LINE, RADIUS = 2, 14
STYLE = f"""
QPushButton {{ color: {INK}; background: {PAPER}; border: {LINE}px solid transparent; border-radius: 9px;
    padding: 6px 12px; font-size: 13px; font-weight: 600; }}
QPushButton:hover {{ background: {PAPER_PRESSED}; }}
QPushButton:checked {{ color: {PAPER}; background: {INK}; }}
QPushButton#finishDrawing {{ background: {ACCENT}; border-color: {INK}; }}
QToolTip {{ color: {PAPER}; background: {INK}; border: none; padding: 4px 8px; }}
"""

GRIP_WIDTH = 22
SWATCH = 22
MARGIN = 24


class ColorSwatch(QPushButton):
    """A round swatch of one pen colour; the one in use wears an outer ring."""

    def __init__(self, color: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.color = QColor(color)
        self.setFixedSize(SWATCH + 8, SWATCH + 8)
        self.setCheckable(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.isChecked():
            painter.setPen(QPen(QColor(INK), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(self.rect().adjusted(2, 2, -2, -2))
        painter.setPen(QPen(QColor(INK), 1))
        painter.setBrush(self.color)
        painter.drawEllipse(self.rect().adjusted(5, 5, -5, -5))


class AnnotationToolbar(QWidget):
    """Tool buttons, colour swatches, undo, clear and finish, floating over the drawing."""

    def __init__(self, overlay: "AnnotationOverlay") -> None:
        # Imported here: the overlay module imports this one for its toolbar.
        from frontengine.show.presentation.annotation_overlay import PEN_COLORS, TOOLS
        super().__init__(overlay)
        self.overlay = overlay
        self.setObjectName("annotationToolbar")
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._drag: Optional[QPoint] = None
        self._moved = False
        layout = QHBoxLayout(self)
        layout.setContentsMargins(GRIP_WIDTH, 8, 12, 8)
        layout.setSpacing(8)
        self.tool_buttons: Dict[str, QPushButton] = {}
        for tool in TOOLS:
            button = tr(QPushButton(), f"annotate_tool_{tool}", tool.title())
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, name=tool: overlay.choose_tool(name))
            self.tool_buttons[tool] = button
            layout.addWidget(button)
        self.swatches: Dict[str, ColorSwatch] = {}
        for name, value in PEN_COLORS:
            swatch = ColorSwatch(value)
            retranslator.bind(swatch, f"color_name_{name.lower()}", name, "setToolTip")
            retranslator.bind(swatch, f"color_name_{name.lower()}", name, "setAccessibleName")
            swatch.clicked.connect(lambda _checked=False, color=value: overlay.choose_color(color))
            self.swatches[value] = swatch
            layout.addWidget(swatch)
        self.undo_button = tr(QPushButton(), "annotate_undo", "Undo")
        self.undo_button.clicked.connect(lambda: overlay.undo())
        self.clear_button = tr(QPushButton(), "annotate_clear", "Clear")
        self.clear_button.clicked.connect(overlay.clear)
        self.finish_button = tr(QPushButton(), "annotate_finish", "Finish (Esc)")
        self.finish_button.setObjectName("finishDrawing")
        self.finish_button.clicked.connect(lambda: overlay.finish_requested.emit())
        for button in (self.undo_button, self.clear_button, self.finish_button):
            layout.addWidget(button)
        for button in (*self.tool_buttons.values(), self.undo_button, self.clear_button, self.finish_button):
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)      # the layer keeps Esc and Ctrl+Z
        self.setStyleSheet(STYLE)
        self.refresh()

    def refresh(self) -> None:
        """Show the tool and colour in use."""
        for tool, button in self.tool_buttons.items():
            button.setChecked(tool == self.overlay.tool)
        for color, swatch in self.swatches.items():
            swatch.setChecked(color == self.overlay.pen_color)

    def place(self) -> None:
        """Bottom centre of the layer until the user drags it; always fully on the layer."""
        self.adjustSize()
        area = self.overlay.rect()
        position = self.pos() if self._moved else QPoint(
            (area.width() - self.width()) // 2, area.height() - self.height() - MARGIN * 3)
        self._move_within(position)

    def _move_within(self, position: QPoint) -> None:
        area = self.overlay.rect()
        self.move(max(0, min(position.x(), area.width() - self.width())),
                  max(0, min(position.y(), area.height() - self.height())))

    def mousePressEvent(self, event) -> None:
        self._drag = event.position().toPoint()
        event.accept()                                     # never a pen stroke under the toolbar

    def mouseMoveEvent(self, event) -> None:
        if self._drag is not None:
            self._moved = True
            self._move_within(self.mapToParent(event.position().toPoint() - self._drag))
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._drag = None
        event.accept()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(INK), LINE))
        painter.setBrush(QColor(PAPER))
        half = LINE / 2
        painter.drawRoundedRect(self.rect().toRectF().adjusted(half, half, -half, -half),
                                RADIUS, RADIUS)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(MUTED))
        for row in range(3):
            for column in range(2):
                painter.drawEllipse(7 + column * 6, self.height() // 2 - 8 + row * 7, 3, 3)
