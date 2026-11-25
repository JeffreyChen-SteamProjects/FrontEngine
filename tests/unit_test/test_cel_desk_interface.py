"""The cel desk: pages wear their group's ink, and the sidebar, sections and header fold away."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QSpinBox, QWidget

from frontengine.ui.nav.shell import NARROW_WINDOW, NavigationPanel
from frontengine.ui.nav.sidebar import KIND_PAGE, RAIL_WIDTH, ROLE_KIND, SIDEBAR_WIDTH, NavigationSidebar
from frontengine.ui.page.layout_kit import FOLDED_KEY, PEG_BAR_HEIGHT, SHORT_PAGE, SettingPage
from frontengine.ui.style.app_style import apply_app_style, contrast_ratio
from frontengine.ui.style.cel import GROUP_PROPERTY, colors_of, spot_for_group, spot_of, tone_of
from frontengine.ui.style.tokens import CEL_OFFSET, DARK, GROUP_SPOTS, LIGHT
from frontengine.user_setting.user_setting_file import user_setting_dict


def _settle():
    for _ in range(4):
        QApplication.processEvents()


@pytest.fixture(autouse=True)
def _own_fold_settings():
    kept = {key: user_setting_dict.get(key) for key in (FOLDED_KEY, "sidebar_compact")}
    user_setting_dict.pop(FOLDED_KEY, None)
    yield
    for key, value in kept.items():
        if value is None:
            user_setting_dict.pop(key, None)
        else:
            user_setting_dict[key] = value


def _page(lifetime_factory, sections=3):
    page = SettingPage("tab_video_text", "page_subtitle_video", "Video", "Play", lifetime=lifetime_factory())
    made = []
    for index in range(sections):
        section = page.add_section(QLabel(f"Section {index}"))
        section.add_row("section_where", QLineEdit(str(index)), "Where")
        made.append(section)
    page.finish_body()
    return page, made


@pytest.mark.parametrize("colors", [LIGHT, DARK])
def test_the_rack_and_the_spot_inks_read(colors):
    assert contrast_ratio(colors["rail"], colors["rail_text"]) >= 7
    assert contrast_ratio(colors["rail"], colors["rail_muted"]) >= 4.5
    assert contrast_ratio(colors["surface"], colors["line"]) >= 3          # a cel's outline shows
    for spot in {*GROUP_SPOTS.values(), "spot_other"}:
        assert contrast_ratio(colors[spot], colors["on_accent"]) >= 4.5, spot     # the icon on its tile
    spots = [colors[name] for name in GROUP_SPOTS.values()]
    assert len(set(spots)) == len(spots)                                   # every group tells itself apart


def test_the_tone_comes_from_the_window_not_from_a_dark_panel_inside_it():
    window = QWidget()
    inner = QWidget(window)
    inner.setStyleSheet("background-color: #000000;")
    apply_app_style(window, "light")
    assert tone_of(inner) == "light"
    apply_app_style(window, "dark")
    assert tone_of(inner) == "dark"
    window.close()


def test_a_page_wears_its_groups_ink_and_a_pet_page_its_paper():
    page, child = QWidget(), QWidget()
    child.setParent(page)
    apply_app_style(page, "light")
    page.setProperty(GROUP_PROPERTY, "nav_group_work")
    assert spot_of(child).name() == QColor(LIGHT["spot_work"]).name()
    assert spot_for_group("plugin group") == "spot_other"
    assert colors_of(child)["window"] == LIGHT["window"]
    page.setProperty("inkStyle", True)
    assert colors_of(child)["window"] == LIGHT["ink_window"]
    page.close()


def test_every_built_in_page_shows_its_icon_under_its_groups_peg_bar(make_main_window):
    window = make_main_window({"language": "English", "theme": "light"})
    window.startup_setting()
    window.showNormal()
    window.resize(1200, 800)
    _settle()
    groups = set()
    for index in range(window.page_stack.count()):
        page = window.page_stack.widget(index)
        window.sidebar.select_page(index)
        _settle()
        assert page.icon_tile.name and page.icon_tile.isVisible(), type(page).__name__
        groups.add(page.property(GROUP_PROPERTY))
        banner = page.banner.grab().toImage()
        ratio = banner.devicePixelRatio()
        assert banner.pixelColor(round(6 * ratio), round(8 * ratio)).name() == spot_of(page).name()
    assert groups == set(GROUP_SPOTS)


def test_a_card_is_a_cel_with_the_sheet_behind_it(*, lifetime_factory):
    page, (section, *_rest) = _page(lifetime_factory)
    page.set_identity("video", "nav_group_on_screen")
    apply_app_style(page, "light")
    page.resize(900, 700)
    page.show()
    _settle()
    image = section.grab().toImage()
    ratio = image.devicePixelRatio()
    middle = image.height() // 2
    right = image.width() - round((CEL_OFFSET / 2 + 1) * ratio)
    assert image.pixelColor(right, middle).name() == QColor(LIGHT["spot_screen"]).name()
    assert image.pixelColor(round(8 * ratio), middle).name() == QColor(LIGHT["surface"]).name()
    page.close()


def test_every_section_folds_from_its_heading_and_is_remembered(*, lifetime_factory):
    page, sections = _page(lifetime_factory)
    page.resize(900, 700)
    page.show()
    _settle()
    first = sections[0]
    tall = first.height()
    QTest.mouseClick(first.title_label, Qt.MouseButton.LeftButton)
    _settle()
    assert not first.expanded and not first.content.isVisible() and first.height() < tall
    assert user_setting_dict[FOLDED_KEY] == {"SettingPage:0": True}
    page.close()
    again, reopened = _page(lifetime_factory)
    assert [section.expanded for section in reopened] == [False, True, True]
    QTest.mouseClick(reopened[0].toggle_button, Qt.MouseButton.LeftButton)
    assert user_setting_dict[FOLDED_KEY] == {"SettingPage:0": False}
    again.close()


def test_a_section_folded_by_default_stays_open_once_opened(*, lifetime_factory):
    page = SettingPage("tab_video_text", lifetime=lifetime_factory())
    page.add_section("section_options", "More", collapsed=True).toggle_button.click()
    page.close()
    again = SettingPage("tab_video_text", lifetime=lifetime_factory())
    assert again.add_section("section_options", "More", collapsed=True).expanded
    again.close()


def test_fold_all_leaves_an_always_open_section_alone(*, lifetime_factory):
    page, sections = _page(lifetime_factory, sections=4)
    sections[0].set_foldable(False)
    page.show()
    assert sections[0].toggle_button.isHidden()
    QTest.mouseClick(sections[0].title_label, Qt.MouseButton.LeftButton)
    assert sections[0].expanded
    page.fold_all_button.click()
    assert [section.expanded for section in sections] == [True, False, False, False]
    folded_text = page.fold_all_button.text()
    page.fold_all_button.click()
    assert all(section.expanded for section in sections)
    assert page.fold_all_button.text() != folded_text
    page.close()


def test_a_small_page_has_no_fold_all_and_damaged_settings_are_ignored(*, lifetime_factory):
    user_setting_dict[FOLDED_KEY] = ["not", "a", "mapping"]
    page, sections = _page(lifetime_factory, sections=2)
    assert page.fold_all_button is None and all(section.expanded for section in sections)
    sections[1].toggle_button.click()
    assert user_setting_dict[FOLDED_KEY] == {"SettingPage:1": True}
    page.close()


def test_a_short_page_gives_its_height_to_the_controls(*, lifetime_factory):
    page, _sections = _page(lifetime_factory)
    page.set_identity("video", "nav_group_on_screen")
    page.resize(800, SHORT_PAGE + 80)
    page.show()
    _settle()
    assert page.subtitle_label.isVisible() and page.icon_tile.isVisible()
    tall = page.banner.height()
    page.resize(800, SHORT_PAGE - 80)
    _settle()
    assert not page.subtitle_label.isVisible() and not page.icon_tile.isVisible()
    assert PEG_BAR_HEIGHT < page.banner.height() < tall
    page.resize(800, SHORT_PAGE + 80)
    _settle()
    assert page.subtitle_label.isVisible() and page.icon_tile.isVisible()
    page.close()


def test_a_page_may_call_one_of_its_fields_height(*, lifetime_factory):
    """The scene's puppet page does; resizing it must not call the field."""
    page, _sections = _page(lifetime_factory)
    page.width, page.height = QSpinBox(page), QSpinBox(page)
    page.show()
    page.resize(700, 300)
    _settle()
    assert not page.subtitle_label.isVisible()
    page.close()


def _panel():
    sidebar = NavigationSidebar()
    sidebar.add_group("nav_group_home", "Home")
    sidebar.add_page("tab_video_text", 0, "Video", icon_name="video")
    sidebar.add_page("tab_image_text", 1, "Image", icon_name="image")
    return NavigationPanel(sidebar)


def test_the_sidebar_folds_to_a_rail_of_icons_with_names_as_tool_tips():
    panel = _panel()
    chosen = []
    panel.compact_changed.connect(chosen.append)
    apply_app_style(panel, "light")
    panel.resize(SIDEBAR_WIDTH, 500)
    panel.show()
    panel.fold_button.click()
    _settle()
    assert panel.compact and panel.sidebar.width() == RAIL_WIDTH and panel.maximumWidth() == RAIL_WIDTH
    assert not panel.brand.name.isVisible() and not panel.search.caption.isVisible()
    for row in range(panel.sidebar.count()):
        item = panel.sidebar.item(row)
        if item.data(ROLE_KIND) == KIND_PAGE:
            assert item.toolTip() == item.text() != ""
    requested = []
    panel.sidebar.page_requested.connect(requested.append)
    panel.sidebar.select_page(1)
    assert requested == [1]
    panel.fold_button.click()
    _settle()
    assert not panel.compact and panel.sidebar.width() == SIDEBAR_WIDTH and panel.brand.name.isVisible()
    assert chosen == [True, False]
    panel.close()


def test_a_narrow_window_folds_the_sidebar_by_itself_and_gives_it_back():
    panel = _panel()
    chosen = []
    panel.compact_changed.connect(chosen.append)
    panel.set_window_width(NARROW_WINDOW - 1)
    assert panel.compact
    panel.toggle()                                   # opened by hand in a narrow window
    assert not panel.compact
    panel.set_window_width(NARROW_WINDOW - 50)       # still narrow: the hand wins
    assert not panel.compact
    panel.set_window_width(NARROW_WINDOW + 100)
    assert not panel.compact
    panel.set_window_width(NARROW_WINDOW - 1)
    assert panel.compact
    panel.set_window_width(NARROW_WINDOW + 100)
    assert not panel.compact and chosen == []        # none of it is the stored choice
    panel.close()


def test_the_window_remembers_the_fold_and_shrinks_past_the_open_sidebar(make_main_window):
    window = make_main_window({"language": "English", "theme": "light"})
    window.resize(1200, 700)
    window.show()
    _settle()
    assert not window.navigation.compact
    window.navigation.fold_button.click()
    assert window.navigation.compact and user_setting_dict["sidebar_compact"] is True
    window.navigation.fold_button.click()
    assert user_setting_dict["sidebar_compact"] is False
    window.resize(536, 500)
    _settle()
    assert window.width() == 536 and window.navigation.compact
    assert user_setting_dict["sidebar_compact"] is False
    window.resize(1200, 700)
    _settle()
    assert not window.navigation.compact


def test_a_stored_fold_is_applied_at_startup(make_main_window):
    window = make_main_window({"language": "English", "theme": "light", "sidebar_compact": True})
    window.resize(1200, 700)
    window.show()
    _settle()
    assert window.navigation.compact


def test_the_selected_tab_runs_into_the_page():
    panel = _panel()
    apply_app_style(panel, "light")
    panel.resize(SIDEBAR_WIDTH, 500)
    panel.show()
    panel.sidebar.select_page(0)
    _settle()
    sidebar = panel.sidebar
    item = next(sidebar.item(row) for row in range(sidebar.count()) if sidebar.item(row).data(ROLE_KIND) == KIND_PAGE)
    rect = sidebar.visualItemRect(item)
    image = sidebar.viewport().grab().toImage()
    ratio = image.devicePixelRatio()
    pixel = image.pixelColor(image.width() - 1, round(rect.center().y() * ratio))
    assert pixel.name() == QColor(LIGHT["window"]).name()
    panel.close()
