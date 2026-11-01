"""The redesigned window frame: sidebar icons and headings, brand mark, command search entry."""
import json
import os

import pytest
from PySide6.QtGui import QIcon

from frontengine.ui.nav.shell import SHORTCUT_HINT, BrandMark, CommandSearchButton
from frontengine.ui.nav.sidebar import KIND_GROUP, KIND_PAGE, ROLE_ICON, ROLE_KIND, NavigationSidebar
from frontengine.ui.style import nav_icons
from frontengine.ui.style.app_style import apply_app_style


def test_every_icon_renders_in_both_tones():
    for name in nav_icons.SHAPES:
        for color in ("#171715", "#F3EEE3"):
            image = nav_icons.pixmap(name, color, 18).toImage()
            assert any(image.pixelColor(x, y).alpha() > 0 for x in range(image.width()) for y in range(0, image.height(), 2)), name


def test_selected_rows_use_the_active_colour():
    icon = nav_icons.icon("video", "#6A6458", "#171715")
    normal = icon.pixmap(18, QIcon.Mode.Normal).toImage()
    selected = icon.pixmap(18, QIcon.Mode.Selected).toImage()
    assert normal != selected


def _rows(sidebar):
    return [sidebar.item(row) for row in range(sidebar.count())]


def test_groups_are_uppercase_and_pages_carry_icons():
    sidebar = NavigationSidebar()
    sidebar.add_group("nav_group_home", "Home")
    sidebar.add_page("tab_video_text", 0, "Video", icon_name="video")
    group, page = _rows(sidebar)
    assert group.data(ROLE_KIND) == KIND_GROUP and group.text() == group.text().upper()
    assert page.data(ROLE_KIND) == KIND_PAGE and page.data(ROLE_ICON) == "video" and not page.icon().isNull()


def test_a_theme_change_redraws_icons_in_the_new_tone():
    sidebar = NavigationSidebar()
    sidebar.add_group("nav_group_home", "Home")
    sidebar.add_page("tab_video_text", 0, "Video", icon_name="video")
    apply_app_style(sidebar, "light")
    before = _rows(sidebar)[1].icon().pixmap(18).toImage()
    apply_app_style(sidebar, "dark")
    after = _rows(sidebar)[1].icon().pixmap(18).toImage()
    assert before != after
    assert sidebar._icon_colors()[1].lower() == "#f3eee3"


def test_folding_swaps_the_chevron():
    sidebar = NavigationSidebar()
    sidebar.add_group("nav_group_home", "Home")
    sidebar.add_page("tab_video_text", 0, "Video", icon_name="video")
    sidebar.add_group("nav_group_work", "Work")
    sidebar.add_page("tab_focus_text", 1, "Focus", icon_name="focus")
    sidebar.select_page(0)
    group = _rows(sidebar)[2]
    open_icon = group.icon().pixmap(18).toImage()
    sidebar.set_group_collapsed("nav_group_work", True)
    assert group.icon().pixmap(18).toImage() != open_icon
    assert _rows(sidebar)[3].isHidden()


def test_brand_and_search_follow_the_theme():
    brand, search = BrandMark(), CommandSearchButton()
    assert search.hint.text() == SHORTCUT_HINT
    apply_app_style(brand, "light")
    apply_app_style(search, "light")
    light = (brand.mark.pixmap().toImage(), search.glass.pixmap().toImage())
    apply_app_style(brand, "dark")
    apply_app_style(search, "dark")
    assert search.glass.pixmap().toImage() != light[1]
    assert not brand.mark.pixmap().isNull()


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


def test_every_built_in_page_has_its_own_icon_and_the_search_opens_commands(window, monkeypatch):
    pages = [item for item in _rows(window.sidebar) if item.data(ROLE_KIND) == KIND_PAGE]
    names = [item.data(ROLE_ICON) for item in pages]
    assert len(names) == 17 and len(set(names)) == 17 and "extension" not in names
    assert window.command_search_button.caption.text() == "Commands"
    opened = []
    monkeypatch.setattr(window, "open_command_palette", lambda: opened.append(True))
    window.command_search_button.clicked.disconnect()
    window.command_search_button.clicked.connect(window.open_command_palette)
    window.command_search_button.click()
    assert opened
    titles = [action.text() for action in window.menu_bar.actions()]
    assert "Help" in titles and "Docs" in titles
