"""
Small layout pieces shared by the dialogs, matching the setting pages.

Buttons placed straight into grid cells stretch to the cell's width, so a pair
such as Add / Remove used to fill the whole dialog. A button row keeps buttons at
their natural size, left-aligned, the way ``Section.add_actions`` does on pages.
"""
from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLayout, QWidget

DIALOG_MARGINS = (18, 16, 18, 14)
DIALOG_SPACING = 10


def button_row(*widgets: QWidget) -> QWidget:
    """Buttons (or small controls) side by side at their own width, then empty space."""
    holder = QWidget()
    holder.setObjectName("inlineActions")
    row = QHBoxLayout(holder)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(8)
    for widget in widgets:
        row.addWidget(widget)
    row.addStretch(1)
    return holder


def roomy(layout: QLayout) -> QLayout:
    """The page-like margins and spacing for a dialog's top-level layout."""
    layout.setContentsMargins(*DIALOG_MARGINS)
    layout.setSpacing(DIALOG_SPACING)
    return layout
