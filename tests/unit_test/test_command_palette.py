"""Localized command selection, bounded preferences and keyboard dispatch."""
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from frontengine.ui.dialog.command_palette_dialog import CommandPaletteDialog
from frontengine.utils.actions.action_registry import Action, ActionRegistry
from frontengine.utils.actions.command_history import CommandHistory
from frontengine.utils.json.json_repository import JsonRepository
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import retranslator


def make_registry(calls):
    registry = ActionRegistry()
    registry.register(Action("capture", "tools_capture_start", "Capture area", lambda value: calls.append(value)))
    registry.register(Action("preset", "rules_action_apply_preset", "Apply preset", calls.append, True))
    return registry


def test_history_survives_reopen_and_never_saves_arguments(tmp_path):
    repository = JsonRepository(tmp_path / "preferences.json")
    settings, calls = {}, []
    history = CommandHistory(settings, lambda: repository.save(settings))
    known = {f"command_{number}" for number in range(30)}
    for identifier in sorted(known):
        history.record(identifier, known)
    history.toggle_favorite("command_3", known)
    reopened = CommandHistory(repository.load(), lambda: None)
    assert len(reopened.values("recent", known)) == 20
    assert reopened.values("favorites", known) == ["command_3"]
    assert not calls
    assert set(repository.load()["command_palette"]) == {"recent", "favorites"}


def test_history_ignores_malformed_unknown_and_duplicate_ids():
    settings = {"command_palette": {"recent": [None, "gone", "capture", "capture"], "favorites": "capture"}}
    history = CommandHistory(settings, lambda: None)
    registry = make_registry([])
    assert history.values("recent", set(registry.actions)) == ["capture"]
    assert history.values("favorites", set(registry.actions)) == []
    history.toggle_favorite("gone", set(registry.actions))
    assert history.search(registry, "CApture", lambda action: action.fallback)[0].identifier == "capture"
    assert not history.search(registry, "unknown", lambda action: action.fallback)


def test_palette_keyboard_search_executes_once_and_records_only_id():
    calls, saved, settings = [], [], {}
    dialog = CommandPaletteDialog(make_registry(calls), CommandHistory(settings, lambda: saved.append(True)))
    dialog.show()
    dialog.search_input.setText("capture")
    QTest.keyClick(dialog.search_input, Qt.Key.Key_Return)
    assert calls == [""] and len(saved) == 1
    assert settings["command_palette"]["recent"] == ["capture"]
    assert not dialog.isVisible()
    dialog.show()
    dialog.search_input.setText("preset")
    dialog.execute_selected()
    assert calls == [""]
    dialog.value_input.setText("Work")
    QTest.keyClick(dialog.value_input, Qt.Key.Key_Return)
    assert calls == ["", "Work"]
    assert "Work" not in str(settings)
    dialog.close()


def test_current_language_search_and_favorite_filter():
    previous = language_wrapper.language
    calls, settings = [], {}
    dialog = CommandPaletteDialog(make_registry(calls), CommandHistory(settings, lambda: None))
    try:
        assert language_wrapper.reset_language("Traditional_Chinese")
        retranslator.apply()
        label = language_wrapper.language_word_dict["tools_capture_start"]
        dialog.search_input.setText(label)
        assert dialog.results.count() == 1 and dialog.selected_id() == "capture"
        dialog.toggle_favorite()
        dialog.search_input.clear()
        dialog.favorites_only.setChecked(True)
        assert dialog.results.count() == 1 and dialog.selected_id() == "capture"
        dialog.toggle_favorite()
        assert dialog.results.count() == 0 and not dialog.run_button.isEnabled()
        assert calls == []
    finally:
        language_wrapper.reset_language(previous)
        retranslator.apply()
        dialog.close()


def test_main_palette_shortcut_opens_and_page_command_routes(monkeypatch):
    from types import MethodType, SimpleNamespace
    from unittest.mock import Mock
    from PySide6.QtWidgets import QMainWindow, QWidget, QApplication
    from frontengine.ui.main_ui import FrontEngineMainUI
    from frontengine.ui.nav.sidebar import NavigationSidebar
    import frontengine.ui.main_ui as module

    monkeypatch.setattr(module, "write_user_setting", lambda: None)
    window = QMainWindow()
    window.menu_bar = window.menuBar()
    window.action_registry = ActionRegistry()
    window.sidebar = NavigationSidebar(window)
    window.sidebar.add_page("tab_tools_text", 0)
    window.command_pages = [(QWidget(window), "tab_tools_text", 0)]
    window.tools_setting_ui = SimpleNamespace(start_capture=Mock())
    window.widgets_setting_ui = SimpleNamespace(add_note=Mock())
    window.screen_care_setting_ui = SimpleNamespace(toggle_filter=Mock())
    window.open_workshop = Mock()
    window.open_command_palette = MethodType(FrontEngineMainUI.open_command_palette, window)
    window._open_command_page = MethodType(FrontEngineMainUI._open_command_page, window)
    FrontEngineMainUI._setup_command_palette(window)
    window.show()
    window.activateWindow()
    QApplication.processEvents()
    QTest.keyClick(window, Qt.Key.Key_K, Qt.KeyboardModifier.ControlModifier)
    QApplication.processEvents()
    assert window.command_palette is not None and window.command_palette.isVisible()
    assert window.action_registry.execute("page.tab_tools_text")
    assert window.sidebar.currentItem().data(Qt.ItemDataRole.UserRole + 1) == 0
    window.command_palette.search_input.setText("capture_area")
    window.command_palette.execute_selected()
    window.tools_setting_ui.start_capture.assert_called_once_with()
    window.command_palette.close()
    window.close()
