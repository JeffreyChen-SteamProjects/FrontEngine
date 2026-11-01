"""Every existing tool stays reachable once the game is the main page."""
import json
import os

import pytest
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu
from shiboken6 import getCppPointer

from frontengine.ui.menu.features_menu import CATEGORIES, run_entry


def _key(action: QAction) -> int:
    """The C++ object; Python wrapper ids are reused once a wrapper is collected."""
    return getCppPointer(action)[0]


@pytest.fixture
def window(tmp_path, monkeypatch):
    from frontengine.ui.main_ui import FrontEngineMainUI
    import frontengine.ui.main_ui as module

    (tmp_path / "user_setting.json").write_text(json.dumps({"language": "English"}), encoding="utf-8")
    original = os.getcwd()
    os.chdir(tmp_path)
    monkeypatch.setattr(module, "write_user_setting", lambda: None)
    try:
        ui = FrontEngineMainUI(show_system_tray_ray=False, redirect_output=False)
        yield ui
        ui.close()
    finally:
        os.chdir(original)


def _actions(menu: QMenu, seen=None) -> list[QAction]:
    """Every action reachable from a menu, following submenus."""
    seen = set() if seen is None else seen
    found = []
    for action in menu.actions():
        if _key(action) in seen:
            continue
        seen.add(_key(action))
        found.append(action)
        if action.menu() is not None:
            found += _actions(action.menu(), seen)
    return found


def test_features_is_the_first_menu(window):
    assert window.menu_bar.actions()[0].menu() is window.features_menu


def test_every_sidebar_page_except_home_has_a_features_entry(window):
    from frontengine.ui.nav.sidebar import KIND_PAGE, ROLE_KIND, ROLE_PAGE_ID
    listed = {entry.target for _key, _fallback, entries in CATEGORIES for entry in entries if entry.kind == "page"}
    pages = {window.sidebar.item(row).data(ROLE_PAGE_ID) for row in range(window.sidebar.count())
             if window.sidebar.item(row).data(ROLE_KIND) == KIND_PAGE}
    assert pages - listed == {"tab_pet_home_text"}
    assert listed <= pages


def test_page_entries_open_their_page_and_count_as_recent(window):
    opened = None
    for _key, _fallback, entries in CATEGORIES:
        for entry in entries:
            if entry.kind != "page":
                continue
            assert run_entry(window, entry) is True
            index = window.sidebar.page_index(entry.target)
            assert window.page_stack.currentIndex() == index
            opened = entry.target
    recent = window.command_history.values("recent", set(window.action_registry.actions))
    assert recent[0] == "page." + opened


def test_every_existing_menu_action_is_reachable_from_features(window):
    features = {_key(action) for action in _actions(window.features_menu)}
    for top in window.menu_bar.actions():
        menu = top.menu()
        if menu is None or menu is window.features_menu:
            continue
        missing = [action.text() for action in _actions(menu)
                   if not action.isSeparator() and _key(action) not in features]
        assert not missing, f"{menu.title()}: {missing}"


def test_command_entries_use_registered_actions(window):
    for _key, _fallback, entries in CATEGORIES:
        for entry in entries:
            if entry.kind == "action":
                assert entry.target in window.action_registry.actions, entry.target
            elif entry.kind == "menu":
                assert isinstance(getattr(window, entry.target), QMenu), entry.target


def test_folded_sidebar_groups_are_remembered_and_unfold_for_their_page(window):
    from frontengine.user_setting.user_setting_file import user_setting_dict
    from frontengine.ui.nav.sidebar import ROLE_GROUP, ROLE_PAGE_ID
    sidebar = window.sidebar
    group = next(sidebar.item(row) for row in range(sidebar.count())
                 if sidebar.item(row).data(ROLE_GROUP) == "nav_group_work")
    sidebar._toggle_if_group(group)
    assert user_setting_dict["sidebar_collapsed_groups"] == ["nav_group_work"]
    tools = next(sidebar.item(row) for row in range(sidebar.count())
                 if sidebar.item(row).data(ROLE_PAGE_ID) == "tab_tools_text")
    assert tools.isHidden()
    assert sidebar.select_page_id("tab_tools_text")
    assert not tools.isHidden()


def test_the_intro_shows_once(window):
    page = window.pet_home_ui
    assert not page.intro_section.isHidden()
    page.dismiss_intro()
    assert page.intro_section.isHidden()
