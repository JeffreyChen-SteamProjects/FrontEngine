"""Accessible-name checks that hold on every platform Qt supports."""
import sys

from PySide6.QtGui import QAccessible
from PySide6.QtWidgets import QComboBox


def assert_named_by(control, label) -> None:
    """The control is announced with its visible label.

    Qt names a combo box by its current text on macOS and hands the label to VoiceOver as its
    title element through the Label relation; elsewhere the label is the accessible name.
    """
    interface = QAccessible.queryAccessibleInterface(control)
    if sys.platform == 'darwin' and isinstance(control, QComboBox):
        related = [other.object() for other, _relation in interface.relations(QAccessible.RelationFlag.Label)]
        assert label in related
    else:
        assert interface.text(QAccessible.Text.Name) == label.text()
