"""FrontEngine's own design system: light / dark tokens, a complete stylesheet and the theme choice."""
import os
import re

import pytest
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QWidget

from frontengine.ui.style import app_style
from frontengine.ui.style.tokens import DARK, LIGHT, THEMES, normalise_theme, resolve_theme
from frontengine.utils.theme_schedule.theme_schedule_service import ThemeScheduleService


@pytest.mark.parametrize("stored, light, dark", [
    ("light", "light", "light"), ("dark", "dark", "dark"), ("system", "light", "dark"), (None, "light", "dark"),
    ("dark_amber.xml", "dark", "dark"), ("light_blue.xml", "light", "light"), ("nonsense", "light", "dark"),
])
def test_stored_names_resolve_to_light_or_dark(stored, light, dark):
    assert resolve_theme(stored, system_dark=False) == light
    assert resolve_theme(stored, system_dark=True) == dark


def test_legacy_qt_material_names_are_normalised():
    assert normalise_theme("dark_teal.xml") == "dark"
    assert normalise_theme("light_cyan_500.xml") == "light"
    assert normalise_theme("LIGHT") == "light"
    assert normalise_theme(42) == "system"
    assert set(THEMES) == {"system", "light", "dark"}


def test_both_palettes_define_the_same_tokens_and_ink_reads_on_the_accent():
    assert set(LIGHT) == set(DARK)
    for colors in (LIGHT, DARK):
        assert app_style.contrast_text(colors["accent"]) == "#000000"   # dark text, as on_accent says
        assert app_style.contrast_ratio(colors["accent"], colors["on_accent"]) >= 4.5
        assert app_style.contrast_ratio(colors["window"], colors["text"]) >= 7
        assert app_style.contrast_ratio(colors["surface"], colors["muted"]) >= 4.5
        assert app_style.contrast_ratio(colors["tooltip"], colors["on_tooltip"]) >= 7


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_stylesheet_styles_every_control_from_the_tokens_only(theme):
    sheet = app_style.build_stylesheet(theme)
    for selector in ("QPushButton", "QLineEdit", "QComboBox", "QSpinBox", "QCheckBox::indicator",
                     "QRadioButton::indicator", "QSlider::handle", "QProgressBar", "QTabBar::tab", "QListView",
                     "QHeaderView::section", "QMenuBar", "QMenu::item", "QToolTip", "QScrollBar",
                     "QPushButton#primaryAction", "QListWidget#navSidebar", "QWidget#settingSection"):
        assert selector in sheet, selector
    tokens = {value.lower() for value in (LIGHT if theme == "light" else DARK).values()}
    literals = {color.lower() for color in re.findall(r"#[0-9a-fA-F]{6}\b", sheet)}
    assert literals <= tokens, literals - tokens
    other = DARK if theme == "light" else LIGHT
    assert other["window"].lower() not in literals


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_every_referenced_icon_ships(theme):
    sheet = app_style.build_stylesheet(theme)
    urls = re.findall(r"url\(([^)]+)\)", sheet)
    assert urls
    for url in urls:
        assert os.path.isfile(url), url


def test_applying_sets_the_palette_and_replaces_the_stylesheet():
    widget = QWidget()
    widget.setStyleSheet("QLabel { color: red; }")
    app_style.apply_app_style(widget, "dark")
    assert "color: red" not in widget.styleSheet()
    assert widget.palette().color(QPalette.ColorRole.Window).name().lower() == DARK["window"].lower()
    assert widget.palette().color(QPalette.ColorRole.Highlight).name().lower() == DARK["accent"].lower()
    app_style.apply_app_style(widget, "light")
    assert widget.palette().color(QPalette.ColorRole.Window).name().lower() == LIGHT["window"].lower()


def test_schedule_defaults_to_light_and_dark_and_refresh_reemits():
    hours = iter([12, 12, 12])
    config = {"enabled": True}
    service = ThemeScheduleService(lambda: config, hour_provider=lambda: next(hours))
    seen = []
    service.theme_changed.connect(seen.append)
    service.poll_once()
    service.poll_once()                     # same theme: nothing new
    service.refresh()                       # re-enabling applies it again
    assert seen == ["light", "light"]


@pytest.fixture
def window(make_main_window):
    return make_main_window({"language": "English", "theme": "dark_amber.xml"})


def test_startup_turns_a_legacy_theme_into_dark_and_the_menu_switches_it(window):
    from frontengine.user_setting.user_setting_file import user_setting_dict
    window.startup_setting()
    assert user_setting_dict["theme"] == "dark"
    assert window.theme_actions["dark"].isChecked()
    window.theme_actions["light"].trigger()
    assert user_setting_dict["theme"] == "light"
    assert window.palette().color(QPalette.ColorRole.Window).name().lower() == LIGHT["window"].lower()


def test_a_scheduled_theme_shows_without_replacing_the_users_choice(window):
    from frontengine.user_setting.user_setting_file import user_setting_dict
    window._apply_theme("light")
    window._apply_scheduled_theme("dark")
    assert user_setting_dict["theme"] == "light"
    assert window.active_theme() == "dark"
    assert window.palette().color(QPalette.ColorRole.Window).name().lower() == DARK["window"].lower()
    window._apply_theme("system")
    assert window.active_theme() == "system"
