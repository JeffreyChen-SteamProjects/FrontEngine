"""
The cel desk, drawn: stacked cels, the peg bar, the light table and its field guide.

A stylesheet cannot draw a sheet behind a card or punch holes in a strip, so the
pieces that make the window FrontEngine's own are painted here, all from the
design tokens of the theme their window was styled with.
"""
from __future__ import annotations

from typing import Dict, Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPalette, QPen
from PySide6.QtWidgets import QWidget

from frontengine.ui.style.tokens import (
    CEL_LINE, CEL_OFFSET, DEFAULT_SPOT, GROUP_SPOTS, INK_LINE, INK_RADIUS_CARD, RADIUS_CARD, palette_for,
)

THEME_PROPERTY = "feTheme"       # "light" or "dark", set on a window by apply_app_style
GROUP_PROPERTY = "navGroup"      # the sidebar group a page belongs to
FIELD_STEP = 26                  # the field guide's spacing
PEG_RADIUS, SLOT_WIDTH, SLOT_HEIGHT, SLOT_GAP = 5.0, 40.0, 8.0, 96.0


def _inherited(widget: Optional[QWidget], name: str):
    """A dynamic property of the widget or its nearest ancestor that has one."""
    while widget is not None:
        value = widget.property(name)
        if value is not None:
            return value
        widget = widget.parentWidget()
    return None


def tone_of(widget: QWidget) -> str:
    """``light`` or ``dark``: the theme the widget's window wears.

    Read from the theme its window was styled with rather than from a palette: a stylesheet
    background rewrites a widget's own palette, so a dark panel in the light theme would read as
    the dark theme."""
    theme = _inherited(widget, THEME_PROPERTY)
    if theme in ("light", "dark"):
        return theme
    return "dark" if widget.palette().color(QPalette.ColorRole.Window).lightness() < 128 else "light"


def colors_of(widget: QWidget) -> Dict[str, str]:
    """The design tokens for this widget, with the pet pages' warm paper where it applies."""
    colors = palette_for(tone_of(widget))
    if _inherited(widget, "inkStyle"):
        return {**colors, "window": colors["ink_window"], "surface": colors["ink_surface"],
                "surface_alt": colors["ink_surface_alt"], "line": colors["ink_line"], "text": colors["ink_text"],
                "muted": colors["ink_muted"], "field": colors["ink_surface_alt"]}
    return colors


def spot_for_group(group: Optional[str]) -> str:
    """The token name of a sidebar group's spot ink."""
    return GROUP_SPOTS.get(group or "", DEFAULT_SPOT)


def spot_of(widget: QWidget) -> QColor:
    """The spot ink of the page the widget is on."""
    return QColor(colors_of(widget)[spot_for_group(_inherited(widget, GROUP_PROPERTY))])


def paint_cel(painter: QPainter, rect: QRectF, colors: Dict[str, str], spot: QColor, *, stacked: bool = True,
              ink: bool = False) -> None:
    """A cel: an ink-outlined sheet, with the sheet behind it showing at the lower right."""
    radius, line = (INK_RADIUS_CARD, INK_LINE) if ink else (RADIUS_CARD, CEL_LINE)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    half = line / 2
    offset = CEL_OFFSET if stacked else 0
    sheet = rect.adjusted(half, half, -half - offset, -half - offset)
    pen = QPen(QColor(colors["line"]), line if stacked else 1)
    painter.setPen(pen)
    if stacked:
        painter.setBrush(spot)
        painter.drawRoundedRect(sheet.translated(offset, offset), radius, radius)
    else:
        painter.setPen(QPen(QColor(colors["border"]), 1))
    painter.setBrush(QColor(colors["surface"]))
    painter.drawRoundedRect(sheet, radius, radius)


def paint_peg_bar(painter: QPainter, rect: QRectF, colors: Dict[str, str], spot: QColor) -> None:
    """The registration strip across the top of a page: a round peg hole between two slots."""
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.fillRect(rect, spot)
    ink = QColor(colors["line"])
    painter.setPen(QPen(ink, CEL_LINE))
    painter.drawLine(QPointF(rect.left(), rect.bottom()), QPointF(rect.right(), rect.bottom()))
    center = QPointF(rect.center().x(), rect.center().y() - CEL_LINE / 2)
    painter.setPen(QPen(ink, 1.6))
    painter.setBrush(QColor(colors["window"]))
    painter.drawEllipse(center, PEG_RADIUS, PEG_RADIUS)
    for side in (-1, 1):
        middle = center.x() + side * SLOT_GAP
        slot = QRectF(middle - SLOT_WIDTH / 2, center.y() - SLOT_HEIGHT / 2, SLOT_WIDTH, SLOT_HEIGHT)
        if rect.left() + 4 < slot.left() and slot.right() < rect.right() - 4:
            painter.drawRoundedRect(slot, SLOT_HEIGHT / 2, SLOT_HEIGHT / 2)


def paint_light_table(painter: QPainter, area: QRectF, colors: Dict[str, str]) -> None:
    """The page background: the table and its field guide, a small cross every FIELD_STEP pixels."""
    painter.fillRect(area, QColor(colors["window"]))
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    painter.setPen(QPen(QColor(colors["field"]), 1))
    left = int(area.left()) - int(area.left()) % FIELD_STEP
    top = int(area.top()) - int(area.top()) % FIELD_STEP
    lines = []
    for x in range(left, int(area.right()) + FIELD_STEP, FIELD_STEP):
        for y in range(top, int(area.bottom()) + FIELD_STEP, FIELD_STEP):
            lines.append((x, y))
    for x, y in lines:
        painter.drawLine(x - 2, y, x + 2, y)
        painter.drawLine(x, y - 2, x, y + 2)


def index_tab(rect: QRectF, radius: float = 9.0) -> QPainterPath:
    """A tab rounded on the left whose right edge runs into the page."""
    path = QPainterPath()
    path.moveTo(rect.right(), rect.top())
    path.lineTo(rect.left() + radius, rect.top())
    path.quadTo(rect.left(), rect.top(), rect.left(), rect.top() + radius)
    path.lineTo(rect.left(), rect.bottom() - radius)
    path.quadTo(rect.left(), rect.bottom(), rect.left() + radius, rect.bottom())
    path.lineTo(rect.right(), rect.bottom())
    path.closeSubpath()
    return path


def paint_icon_tile(painter: QPainter, rect: QRectF, colors: Dict[str, str], spot: QColor) -> None:
    """The spot-ink tile a page's icon sits on."""
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(colors["line"]), CEL_LINE))
    painter.setBrush(spot)
    inset = CEL_LINE / 2
    painter.drawRoundedRect(rect.adjusted(inset, inset, -inset, -inset), 11, 11)


def set_hand(widget: QWidget) -> None:
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
