import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget

_OVERLAY_BASE_FLAGS = (
    Qt.WindowType.WindowTransparentForInput
    | Qt.WindowType.FramelessWindowHint
    | Qt.WindowType.Tool
)


def apply_overlay_window_flags(
    widget: QWidget,
    show_on_bottom: bool = False,
    allow_input: bool = False,
) -> None:
    """
    Apply the shared "overlay" window flag combination to a widget.

    allow_input=True omits WindowTransparentForInput so the widget can still
    receive mouse/keyboard (used by the web overlay when the user opts in).
    """
    flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
    if not allow_input:
        flags |= Qt.WindowType.WindowTransparentForInput
    if show_on_bottom:
        flags |= Qt.WindowType.WindowStaysOnBottomHint
    else:
        flags |= Qt.WindowType.WindowStaysOnTopHint
    widget.setWindowFlags(flags)


def load_overlay_icon(widget: QWidget) -> None:
    """Set the shared frontengine.ico as the widget's window icon if present."""
    icon_path = Path(os.getcwd()) / "frontengine.ico"
    if icon_path.exists() and icon_path.is_file():
        widget.setWindowIcon(QIcon(str(icon_path)))
