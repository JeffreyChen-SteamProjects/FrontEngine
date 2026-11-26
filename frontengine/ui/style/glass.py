"""
Glass panels, drawn: translucent sheets with a lit edge and a soft shadow.

The window behind them is ``backdrop.py``, already blurred, so a panel only has to
tint it; nothing here needs a translucent window, which some GPUs turn black. All
colours come from the design tokens of the theme their window was styled with.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Dict, Optional, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPalette, QPen
from PySide6.QtWidgets import QWidget

from frontengine.ui.style.tokens import RADIUS_CARD, RADIUS_NESTED, SHADOW_DEPTH, palette_for

THEME_PROPERTY = "feTheme"       # "light" or "dark", set on a window by apply_app_style


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
    """The design tokens for this widget; the pet pages' panels carry a warm tint."""
    colors = palette_for(tone_of(widget))
    if _inherited(widget, "inkStyle"):
        return {**colors, "glass": colors["glass_warm"]}
    return colors


@lru_cache(maxsize=256)
def _shadow_paths(width: float, height: float, radius: float) -> Tuple[QPainterPath, ...]:
    """The slivers of each shadow layer that show below a panel of this size, at the origin.

    Only those are painted: under the panel they would show through it, and filling the panel's
    whole area once per layer made scrolling a page of panels slow."""
    panel = QPainterPath()
    panel.addRoundedRect(QRectF(0, 0, width, height), radius, radius)
    layers = []
    for step in range(SHADOW_DEPTH, 0, -2):
        layer = QPainterPath()
        layer.addRoundedRect(QRectF(6 - step / 2, 4, width - 12 + step, height - 4 + step), radius, radius)
        layers.append(layer.subtracted(panel))
    return tuple(layers)


def _paint_shadow(painter: QPainter, sheet: QRectF, color: QColor, radius: float) -> None:
    painter.save()
    painter.translate(sheet.topLeft())
    for step, layer in zip(range(SHADOW_DEPTH, 0, -2), _shadow_paths(sheet.width(), sheet.height(), radius)):
        shade = QColor(color)
        shade.setAlpha(max(1, round(color.alpha() * (1 - step / (SHADOW_DEPTH + 2)) / 2.2)))
        painter.fillPath(layer, shade)
    painter.restore()


def paint_panel(painter: QPainter, rect: QRectF, colors: Dict[str, str], *, nested: bool = False,
                radius: Optional[float] = None) -> None:
    """A glass sheet: tint, lit edge and, unless nested in another panel, a shadow below it."""
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    if radius is None:
        radius = RADIUS_NESTED if nested else RADIUS_CARD
    sheet = rect.adjusted(.5, .5, -.5, -.5 - (0 if nested else SHADOW_DEPTH))
    path = QPainterPath()
    path.addRoundedRect(sheet, radius, radius)
    if not nested:
        _paint_shadow(painter, sheet, QColor(colors["shadow"]), radius)
    painter.fillPath(path, QColor(colors["glass_nested" if nested else "glass"]))
    edge = QLinearGradient(QPointF(0, sheet.top()), QPointF(0, sheet.bottom()))
    edge.setColorAt(0, QColor(colors["glass_edge"]))
    edge.setColorAt(1, QColor(colors["glass_edge_low"]))
    painter.setPen(QPen(edge, 1))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(path)


def set_hand(widget: QWidget) -> None:
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
