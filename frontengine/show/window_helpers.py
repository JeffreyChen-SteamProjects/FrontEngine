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
    # 記住這次的選擇，之後鎖定／解鎖時才能保持同樣的堆疊層級
    # Remember the choice so lock/unlock keeps the same stacking level.
    widget.overlay_show_on_bottom = bool(show_on_bottom)
    widget.overlay_locked = not bool(allow_input)


def set_overlay_locked(widget: QWidget, locked: bool) -> bool:
    """
    鎖定覆蓋層＝點擊穿透（滑鼠事件直接落到底下的程式）；解鎖＝可以接收滑鼠、
    用拖曳調整位置。回傳是否真的切換（不可鎖定的覆蓋層如寵物會回傳 False）。

    Locking an overlay makes it click-through so clicks reach whatever is
    behind it; unlocking lets it take the mouse so it can be dragged into
    place. Returns False for overlays that opt out of locking (e.g. the pet).
    """
    if not getattr(widget, "overlay_lockable", True):
        return False
    was_visible = widget.isVisible()
    apply_overlay_window_flags(
        widget,
        show_on_bottom=getattr(widget, "overlay_show_on_bottom", False),
        allow_input=not locked,
    )
    # 變更 window flags 會讓視窗被隱藏，原本看得見的要重新顯示
    # Changing window flags hides the window, so show it again if it was visible.
    if was_visible:
        widget.show()
    return True


def load_overlay_icon(widget: QWidget) -> None:
    """Set the shared frontengine.ico as the widget's window icon if present."""
    icon_path = Path(os.getcwd()) / "frontengine.ico"
    if icon_path.exists() and icon_path.is_file():
        widget.setWindowIcon(QIcon(str(icon_path)))
