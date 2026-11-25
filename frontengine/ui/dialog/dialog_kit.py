"""
Small layout pieces shared by the dialogs, matching the setting pages.

Buttons placed straight into grid cells stretch to the cell's width, so a pair
such as Add / Remove used to fill the whole dialog. A button row keeps buttons at
their natural size, left-aligned, the way ``Section.add_actions`` does on pages.
"""
from __future__ import annotations

from typing import Any, Callable, Dict

from PySide6.QtWidgets import QHBoxLayout, QLayout, QMessageBox, QWidget

from frontengine.user_setting.user_setting_file import user_setting_dict

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


def save_or_tell(dialog: QWidget, values: Dict[str, Any], write: Callable[[], Any]) -> bool:
    """Store these settings and save them. Failing that, put the old ones back and say why; the dialog
    stays open with the choices on it."""
    previous = {key: user_setting_dict[key] for key in values if key in user_setting_dict}
    user_setting_dict.update(values)
    try:
        write()
        return True
    except (OSError, ValueError) as error:
        for key in values:
            if key in previous:
                user_setting_dict[key] = previous[key]
            else:
                user_setting_dict.pop(key, None)
        QMessageBox.warning(dialog, dialog.windowTitle(), str(error))
        return False
