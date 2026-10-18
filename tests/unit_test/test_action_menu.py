"""Secondary actions stay reachable, localized and in sync with their owners."""
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton

from frontengine.ui.page.action_menu import ActionMenu
from frontengine.ui.page.layout_kit import SettingPage
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import retranslator, tr, translate


def test_menu_dispatches_once_and_respects_disabled_commands():
    calls = []
    first, second = QPushButton("Copy"), QPushButton("Edit")
    first.clicked.connect(lambda: calls.append("copy"))
    second.clicked.connect(lambda: calls.append("edit"))
    second.setEnabled(False)
    menu = ActionMenu((first, second))
    try:
        actions = menu.menu().actions()
        assert [action.text() for action in actions] == ["Copy", "Edit"]
        assert not actions[1].isEnabled()
        actions[0].trigger()
        assert calls == ["copy"]
        second.setEnabled(True)
        assert actions[1].isEnabled()
        actions[1].trigger()
        assert calls == ["copy", "edit"]
    finally:
        menu.close()


def test_menu_updates_toggled_labels_and_current_language():
    previous = language_wrapper.language
    button = tr(QPushButton(), "control_center_mute_all")
    button.clicked.connect(lambda: retranslator.set_text(button, "control_center_unmute_all"))
    menu = ActionMenu((button,))
    try:
        menu.menu().actions()[0].trigger()
        menu.menu().aboutToShow.emit()
        assert menu.menu().actions()[0].text() == translate("control_center_unmute_all")
        language_wrapper.reset_language("Deutsch")
        retranslator.apply()
        assert menu.text() == translate("ui_more_actions")
        assert menu.menu().actions()[0].text() == translate("control_center_unmute_all")
    finally:
        language_wrapper.reset_language(previous)
        retranslator.apply()
        menu.close()


def test_collapsing_settings_preserves_input_and_keyboard_access():
    page = SettingPage("tab_tools_text")
    section = page.add_section("section_appearance", collapsed=True)
    field = QLineEdit("Keep this value")
    section.add_row("url", field)
    page.finish_body()
    try:
        page.resize(700, 500)
        page.show()
        QApplication.processEvents()
        assert not field.isVisible()
        section.toggle_button.setFocus()
        QTest.keyClick(section.toggle_button, Qt.Key.Key_Space)
        assert field.isVisible()
        field.setText("Edited value")
        QTest.keyClick(section.toggle_button, Qt.Key.Key_Space)
        assert not field.isVisible()
        QTest.keyClick(section.toggle_button, Qt.Key.Key_Space)
        assert field.isVisible() and field.text() == "Edited value"
    finally:
        page.close()
