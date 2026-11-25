"""Names in the pet home read on its own sky, and its tabs' sections show no empty heading."""
import pytest
from PySide6.QtWidgets import QApplication

from frontengine.show.pet_game.themes import PALETTES, sky_color
from frontengine.ui.page.layout_kit import Section
from frontengine.ui.style.app_style import contrast_ratio


@pytest.mark.parametrize("app_theme", ["light", "dark"])
def test_names_read_on_the_sky_at_every_hour_in_either_theme(make_main_window, app_theme):
    window = make_main_window({"language": "English", "theme": app_theme})
    window.startup_setting()
    page = window.pet_home_ui
    page.create_home()
    world, view = page.service.world, page.view
    zone = world.zones[page.zone]
    QApplication.processEvents()
    day = 60 * 60 * 1000                        # a game day is one real hour
    for theme in PALETTES:
        zone.theme = theme
        for step in range(48):
            world.time_ms = day * step // 48
            sky = sky_color(theme, world.time_ms, False)
            assert contrast_ratio(sky.name(), view.ink().name()) >= 4, (theme, step)


def test_a_section_shown_as_a_tab_has_no_chevron_of_its_own(make_main_window):
    page = make_main_window().pet_home_ui
    page.create_home()
    untitled = [section for section in page.tabs.findChildren(Section) if section.title_label.isHidden()]
    assert len(untitled) >= 5                   # a tab each: otherwise this checks nothing
    for section in untitled:
        assert section.toggle_button.isHidden()
