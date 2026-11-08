import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from frontengine.ui.page.wrapping_buttons import WrappingCheckBox, WrappingPushButton


@pytest.mark.parametrize('button_type', [WrappingCheckBox, WrappingPushButton])
def test_wrapped_caption_keeps_native_click_and_keyboard_behavior(button_type):
    host = QWidget()
    layout = QVBoxLayout(host)
    text = 'Pets 🐾 work alongside my focus sessions, including longer translated captions.'
    check = button_type(text)
    check.setCheckable(True)
    layout.addWidget(check)
    host.resize(180, 180)
    host.show()
    try:
        QApplication.processEvents()
        assert check.width() < 180
        assert check.height() >= check.heightForWidth(check.width())
        assert check.height() > check.fontMetrics().height() * 2
        long_height = check.heightForWidth(check.width())
        assert check.text() == text
        QTest.mouseClick(check, Qt.MouseButton.LeftButton, pos=QPoint(check.width() - 2, check.height() - 2))
        assert check.isChecked()
        check.setFocus()
        QTest.keyClick(check, Qt.Key.Key_Space)
        assert not check.isChecked()
        check.setText('Short caption')
        QApplication.processEvents()
        assert check.text() == 'Short caption'
        assert check.heightForWidth(check.width()) < long_height
    finally:
        host.close()
