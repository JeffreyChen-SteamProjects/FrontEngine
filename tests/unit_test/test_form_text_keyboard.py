"""Multiline form fields allow keyboard access to their following controls."""
import pytest
from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtTest import QTest

from frontengine.ui.dialog.screen_text_dialog import ScreenTextDialog
from frontengine.ui.dialog.signage_dialog import SignageDialog


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
