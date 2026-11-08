"""Multiline form fields allow keyboard access to their following controls."""
import pytest
from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtTest import QTest

from frontengine.ui.dialog.screen_text_dialog import ScreenTextDialog
from frontengine.ui.dialog.signage_dialog import SignageDialog


@pytest.mark.parametrize('field,label_name', [('presets_edit', 'presets_label'),
                                             ('interval_spinbox', 'interval_label')])
def test_signage_accessible_name_tracks_visible_label_without_editing_settings(field, label_name):
    from PySide6.QtGui import QAccessible

    dialog = SignageDialog()
    try:
        dialog.presets_edit.setPlainText('Morning\nEvening')
        before = dialog.settings()
        control = getattr(dialog, field)
        label = getattr(dialog, label_name)
        accessible = QAccessible.queryAccessibleInterface(control)
        assert accessible.text(QAccessible.Text.Name) == label.text()
        label.setText('Updated ' + label.text())
        assert accessible.text(QAccessible.Text.Name) == label.text()
        assert dialog.settings() == before
    finally:
        dialog.reject()


@pytest.mark.parametrize('kind', ['screen_text', 'signage'])
def test_multiline_form_tab_preserves_text_and_enter_inserts_line(kind):
    dialog = ScreenTextDialog('First line') if kind == 'screen_text' else SignageDialog()
    editor = dialog.text_edit if kind == 'screen_text' else dialog.presets_edit
    next_control = dialog.copy_button if kind == 'screen_text' else dialog.interval_spinbox
    editor.setPlainText('First line')
    try:
        dialog.show()
        dialog.activateWindow()
        editor.setFocus()
        QCoreApplication.processEvents()
        QTest.keyClick(editor, Qt.Key.Key_Tab)
        assert next_control.hasFocus()
        assert editor.toPlainText() == 'First line'
        QTest.keyClick(next_control, Qt.Key.Key_Backtab)
        assert editor.hasFocus()
        QTest.keyClick(editor, Qt.Key.Key_End)
        QTest.keyClick(editor, Qt.Key.Key_Return)
        QTest.keyClicks(editor, 'Second line')
        assert editor.toPlainText() == 'First line\nSecond line'
        if kind == 'signage':
            assert dialog.settings()['presets'] == ['First line', 'Second line']
    finally:
        dialog.reject()
