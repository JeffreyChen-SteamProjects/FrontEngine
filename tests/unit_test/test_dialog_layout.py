"""Dialogs follow the pages: buttons keep their own width, the closing default stands out."""
import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QDialog, QPushButton

from frontengine.ui.dialog.dialog_kit import DIALOG_MARGINS, button_row, roomy
from frontengine.ui.style.app_style import build_stylesheet


def test_a_button_row_keeps_buttons_at_their_own_width():
    first, second = QPushButton("Add"), QPushButton("Remove")
    row = button_row(first, second)
    row.resize(900, 40)
    row.show()
    QCoreApplication.processEvents()
    assert first.width() < 200
    assert second.width() < 200
    assert first.x() < second.x()
    row.close()


@pytest.mark.parametrize("module, name, buttons", [
    ("app_profile_dialog", "AppProfileDialog", ("add_button", "remove_button")),
    ("reminder_dialog", "ReminderDialog", ("add_button", "remove_button")),
    ("rules_dialog", "RulesDialog", ("add_button", "remove_button", "preview_button", "history_button")),
    ("window_pin_dialog", "WindowPinDialog", ("refresh_button", "pin_button", "unpin_button")),
])
def test_dialog_buttons_no_longer_fill_the_dialog(module, name, buttons):
    import importlib
    cls = getattr(importlib.import_module("frontengine.ui.dialog." + module), name)
    parent = QDialog()
    dialog = cls(parent)
    dialog.resize(900, 600)
    dialog.show()
    QCoreApplication.processEvents()
    try:
        for attribute in buttons:
            assert getattr(dialog, attribute).width() < dialog.width() / 3, attribute
        margins = dialog.layout().contentsMargins()
        assert (margins.left(), margins.top()) == DIALOG_MARGINS[:2]
    finally:
        dialog.close()
        parent.close()


def test_hotkey_fields_are_wide_enough_for_a_whole_chord():
    from frontengine.ui.dialog.hotkey_settings_dialog import HotkeySettingsDialog
    parent = QDialog()
    dialog = HotkeySettingsDialog(parent)
    dialog.show()
    QCoreApplication.processEvents()
    try:
        edit = next(iter(dialog._edits.values()))
        assert edit.width() >= edit.fontMetrics().horizontalAdvance("<ctrl>+<shift>+<f12>")
    finally:
        dialog.close()
        parent.close()


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_the_closing_default_button_is_the_accent(theme):
    sheet = build_stylesheet(theme)
    assert "QDialogButtonBox QPushButton:default" in sheet


def test_roomy_sets_page_like_margins():
    from PySide6.QtWidgets import QVBoxLayout
    layout = roomy(QVBoxLayout())
    assert layout.contentsMargins().right() == DIALOG_MARGINS[2]
