"""The glass look: panels over a blurred backdrop, and a window that folds away."""
from functools import reduce

import numpy
import pytest
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QSpinBox, QWidget

from frontengine.ui.nav.shell import (
    NARROW_WINDOW, PANEL_WIDTH, RAIL_PANEL_WIDTH, NavigationPanel, OverlayStatusBar,
)
from frontengine.ui.nav.sidebar import KIND_PAGE, RAIL_WIDTH, ROLE_KIND, SIDEBAR_WIDTH, NavigationSidebar
from frontengine.ui.page.layout_kit import FOLDED_KEY, SHORT_PAGE, SettingPage
from frontengine.ui.style import backdrop as backdrop_module
from frontengine.ui.style.app_style import apply_app_style, relative_luminance
from frontengine.ui.style.backdrop import Backdrop, built_in, tinted
from frontengine.ui.style.glass import colors_of, tone_of
from frontengine.ui.style.tokens import DARK, LIGHT, palette_for
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


def _over(ground, token):
    color = QColor(token)
    alpha = color.alphaF()
    return ground * (1 - alpha) + numpy.array([color.red(), color.green(), color.blue()]) * alpha


def _contrast(first, second):
    names = ["#%02x%02x%02x" % tuple(int(round(float(channel))) for channel in color) for color in (first, second)]
    lighter, darker = sorted((relative_luminance(name) for name in names), reverse=True)
    return (lighter + .05) / (darker + .05)


LAYERS = {"bare": [], "panel": ["glass"], "pet panel": ["glass_warm"], "nested": ["glass", "glass_nested"],
          "field": ["glass", "well"]}


@pytest.mark.parametrize("tone", ["light", "dark"])
def test_text_reads_over_any_wallpaper(tone):
    """The wallpaper is the user's: pure white, black and every saturated corner have to work."""
    colors = palette_for(tone)
    corners = numpy.array([[(red, green, blue) for red in (0, 128, 255) for green in (0, 128, 255)
                            for blue in (0, 128, 255)]], dtype=numpy.float32)
    own = built_in(tone).reshape(-1, 3)
    grounds = [*tinted(corners, tone)[0], own[own.sum(1).argmax()], own[own.sum(1).argmin()]]
    for layer, stack in LAYERS.items():
        for name, least in (("text", 4.5), ("muted", 4.2 if layer == "nested" else 4.5)):
            ink = QColor(colors[name])
            ink = numpy.array([ink.red(), ink.green(), ink.blue()])
            worst = min(_contrast(reduce(_over, [colors[key] for key in stack], ground), ink) for ground in grounds)
            assert worst >= least, (tone, layer, name, worst)


def test_the_wallpaper_is_blurred_tinted_and_noticed_when_it_changes(tmp_path):
    picture = tmp_path / "wallpaper.png"

    def write(left, right):
        image = QImage(320, 180, QImage.Format.Format_RGB32)
        image.fill(QColor(left))
        painter = QPainter(image)
        painter.fillRect(QRect(160, 0, 160, 180), QColor(right))
        painter.end()
        assert image.save(str(picture))

    write("#c02020", "#2020c0")
    backdrop = Backdrop(lambda: picture)
    assert backdrop.refresh() and backdrop.shows_wallpaper
    first = backdrop.image("dark")
    left, middle, right = (first.pixelColor(x, 130) for x in (20, 240, 460))
    assert left.red() > left.blue() and right.blue() > right.red()
    assert abs(middle.red() - middle.blue()) < abs(left.red() - left.blue())      # no hard edge survives
    assert not backdrop.refresh()
    write("#20c020", "#20c020ff")
    import os
    os.utime(picture, (1, 1))
    assert backdrop.refresh()
    assert backdrop.image("dark").pixelColor(20, 130).green() > left.green()
    assert backdrop.set_use_wallpaper(False) and not backdrop.shows_wallpaper


@pytest.mark.parametrize("content", [b"", b"not a picture", None])
def test_an_unusable_wallpaper_falls_back_to_the_built_in_picture(tmp_path, content):
    path = tmp_path / "wallpaper.jpg"
    if content is not None:
        path.write_bytes(content)
    backdrop = Backdrop(lambda: path)
    backdrop.refresh()
    assert not backdrop.shows_wallpaper
    for tone in ("light", "dark"):
        assert not backdrop.image(tone).isNull()


def test_a_huge_wallpaper_file_is_not_read(tmp_path, monkeypatch):
    path = tmp_path / "wallpaper.png"
    QImage(8, 8, QImage.Format.Format_RGB32).save(str(path))
    monkeypatch.setattr(backdrop_module, "MAX_FILE_BYTES", 10)
    backdrop = Backdrop(lambda: path)
    backdrop.refresh()
    assert not backdrop.shows_wallpaper


def test_the_tone_comes_from_the_window_not_from_a_panel_inside_it():
    window = QWidget()
    inner = QWidget(window)
    inner.setStyleSheet("background-color: #000000;")
    apply_app_style(window, "light")
    assert tone_of(inner) == "light"
    apply_app_style(window, "dark")
    assert tone_of(inner) == "dark"
    window.close()


def test_pet_pages_wear_a_warm_panel():
    page, child = QWidget(), QWidget()
    child.setParent(page)
    apply_app_style(page, "light")
    assert colors_of(child)["glass"] == LIGHT["glass"]
    page.setProperty("inkStyle", True)
    assert colors_of(child)["glass"] == LIGHT["glass_warm"]
    page.close()


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_the_backdrop_shows_through_every_page(make_main_window, theme):
    window = make_main_window({"language": "English", "theme": theme})
    window.startup_setting()
    window.showNormal()
    window.resize(1200, 820)
    _settle()
    ground = window.backdrop.image(theme).scaled(window.size())
    for index in range(window.page_stack.count()):
        window.sidebar.select_page(index)
        _settle()
        image = window.grab().toImage()
        ratio = image.devicePixelRatio()
        # beside the centred column, level with the page's title: nothing is there but the backdrop
        x, y = window.width() - 16, 200
        seen, expected = image.pixelColor(round(x * ratio), round(y * ratio)), ground.pixelColor(x, y)
        for channel in ("red", "green", "blue"):
            assert abs(getattr(seen, channel)() - getattr(expected, channel)()) <= 6, type(
                window.page_stack.widget(index)).__name__


def test_the_wallpaper_choice_is_kept_and_applied(make_main_window, monkeypatch, tmp_path):
    picture = tmp_path / "desk.png"
    image = QImage(64, 36, QImage.Format.Format_RGB32)
    image.fill(QColor("#208040"))
    image.save(str(picture))
    monkeypatch.setattr(backdrop_module, "desktop_wallpaper", lambda: picture)
    window = make_main_window({"language": "English", "theme": "dark"})
    assert window.backdrop.shows_wallpaper and window.wallpaper_backdrop_action.isChecked()
    window.wallpaper_backdrop_action.trigger()
    assert user_setting_dict["wallpaper_backdrop"] is False and not window.backdrop.shows_wallpaper
    again = make_main_window({"language": "English", "theme": "dark", "wallpaper_backdrop": False})
    assert not again.backdrop.shows_wallpaper and not again.wallpaper_backdrop_action.isChecked()


def test_a_section_is_a_panel_lighter_than_the_dark_backdrop(*, lifetime_factory):
    page, (section, *_rest) = _page(lifetime_factory)
    apply_app_style(page, "dark")
    page.resize(900, 700)
    page.show()
    _settle()
    image = page.grab().toImage()
    ratio = image.devicePixelRatio()
    spot = section.mapTo(page, section.rect().center())
    inside = image.pixelColor(round((section.mapTo(page, section.rect().topLeft()).x() + 8) * ratio),
                              round(spot.y() * ratio))
    assert inside.lightness() > QColor(DARK["window"]).lightness()
    page.close()


def _status(overlays):
    bar = OverlayStatusBar(lambda: overlays)
    bar.refresh()
    return bar


def test_the_status_bar_counts_what_is_on_screen_and_offers_the_right_action():
    shown, hidden = QWidget(), QWidget()
    shown.show()
    overlays = [shown, hidden, shown]                # listed twice by two pages: one overlay
    bar = _status(overlays)
    asked, closed = [], []
    bar.toggle_requested.connect(asked.append)
    bar.close_requested.connect(lambda: closed.append(True))
    assert (bar.visible_count, bar.hidden_count) == (1, 1) and "1" in bar.text.text()
    bar.toggle_button.click()
    shown.hide()
    bar.refresh()
    hide_text = bar.toggle_button.text()
    bar.toggle_button.click()
    bar.close_button.click()
    assert asked == [True, False] and closed == [True]
    overlays.clear()
    bar.refresh()
    assert not bar.toggle_button.isEnabled() and not bar.close_button.isEnabled()
    assert bar.toggle_button.text() != hide_text
    for widget in (shown, hidden, bar):
        widget.close()


def test_the_status_bar_survives_a_deleted_overlay_and_only_polls_while_shown():
    from shiboken6 import delete
    gone = QWidget()
    bar = _status([gone])
    delete(gone)
    bar.refresh()
    assert (bar.visible_count, bar.hidden_count) == (0, 0)
    assert not bar._timer.isActive()
    bar.show()
    assert bar._timer.isActive()
    bar.hide()
    assert not bar._timer.isActive()
    bar.close()


def test_the_status_bar_acts_on_the_control_center(make_main_window):
    window = make_main_window({"language": "English", "theme": "light"})
    window.resize(1200, 800)
    window.show()
    _settle()
    overlay = QWidget()
    overlay.show()
    window.image_setting_ui.image_widget_list.append(overlay)
    bar = window.overlay_status
    try:
        bar.refresh()
        assert bar.visible_count == 1
        bar.toggle_button.click()
        assert not overlay.isVisible() and bar.hidden_count == 1
        bar.toggle_button.click()
        assert overlay.isVisible()
        bar.close_button.click()
        assert window.image_setting_ui.image_widget_list == [] and bar.visible_count == 0
    finally:
        overlay.close()
    window.resize(1200, 500)
    _settle()
    assert not bar.isVisible()                       # a short window keeps the height for the page


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
    page.resize(800, SHORT_PAGE + 80)
    page.show()
    _settle()
    assert page.subtitle_label.isVisible()
    tall = page.banner.height()
    page.resize(800, SHORT_PAGE - 80)
    _settle()
    assert not page.subtitle_label.isVisible() and page.banner.height() < tall
    page.resize(800, SHORT_PAGE + 80)
    _settle()
    assert page.subtitle_label.isVisible()
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
    panel.resize(PANEL_WIDTH, 500)
    panel.show()
    panel.fold_button.click()
    _settle()
    assert panel.compact and panel.sidebar.width() == RAIL_WIDTH and panel.maximumWidth() == RAIL_PANEL_WIDTH
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


def test_the_selected_page_is_a_solid_pill():
    panel = _panel()
    apply_app_style(panel, "light")
    panel.resize(PANEL_WIDTH, 500)
    panel.show()
    panel.sidebar.select_page(0)
    _settle()
    sidebar = panel.sidebar
    item = next(sidebar.item(row) for row in range(sidebar.count()) if sidebar.item(row).data(ROLE_KIND) == KIND_PAGE)
    rect = sidebar.visualItemRect(item)
    image = sidebar.viewport().grab().toImage()
    ratio = image.devicePixelRatio()
    pixel = image.pixelColor(round((rect.right() - 20) * ratio), round(rect.center().y() * ratio))
    assert pixel.name() == QColor(LIGHT["pill"]).name()
    panel.close()


def test_the_heading_chevron_sits_at_the_right_edge(*, lifetime_factory):
    page, (section, *_rest) = _page(lifetime_factory)
    page.resize(900, 700)
    page.show()
    _settle()
    right = section.toggle_button.geometry().right()
    assert section.width() - right <= 30
    assert section.toggle_button.y() == section.title_label.y()
    page.close()
