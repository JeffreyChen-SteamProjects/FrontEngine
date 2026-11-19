"""FrontEngine's own design system: light / dark tokens, a complete stylesheet and the theme choice."""
import os
import re

import pytest
from PySide6.QtGui import QPalette
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication, QLineEdit, QListView, QListWidget, QTableView, QTableWidget,
    QTreeView, QTreeWidget, QVBoxLayout, QWidget,
)

from frontengine.ui.style import app_style
from frontengine.ui.style.tokens import DARK, LIGHT, THEMES, normalise_theme, resolve_theme
from frontengine.utils.theme_schedule.theme_schedule_service import ThemeScheduleService


@pytest.mark.parametrize('theme', ['light', 'dark'])
@pytest.mark.parametrize('view_type', [QListView, QListWidget, QTreeView, QTreeWidget, QTableView, QTableWidget])
def test_item_view_focus_is_visible_without_selection_or_resizing(theme, view_type):
    host = QWidget()
    layout = QVBoxLayout(host)
    entry, view = QLineEdit(), view_type()
    layout.addWidget(entry)
    layout.addWidget(view)
    app_style.apply_app_style(host, theme)
    host.resize(360, 240)
    host.show()
    try:
        entry.setFocus()
        QApplication.processEvents()
        before = view.grab().toImage()
        geometry = view.geometry()
        QTest.keyClick(entry, Qt.Key.Key_Tab)
        QApplication.processEvents()
        assert view.hasFocus()
        after = view.grab().toImage()
        assert view.geometry() == geometry
        assert before.copy(0, 0, before.width(), 1) != after.copy(0, 0, after.width(), 1), (
            f'{view_type.__name__} {theme}: border does not change when keyboard focus enters')
    finally:
        host.close()


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
        # The pet pages' ink look reads as well as the tools do.
        assert app_style.contrast_ratio(colors["ink_window"], colors["ink_text"]) >= 7
        assert app_style.contrast_ratio(colors["ink_surface"], colors["ink_text"]) >= 7
        assert app_style.contrast_ratio(colors["ink_surface"], colors["ink_muted"]) >= 4.5
        assert app_style.contrast_ratio(colors["ink_line"], colors["ink_selected_text"]) >= 7
        assert app_style.contrast_ratio(colors["ink_surface"], colors["ink_line"]) >= 3     # the outline shows


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_ink_rules_reach_only_widgets_under_ink_style(theme):
    """Every rule using an ink colour is scoped to inkStyle, so the tool pages keep the quiet look."""
    sheet = app_style.build_stylesheet(theme)
    colors = LIGHT if theme == "light" else DARK
    ink_values = {colors[key].lower() for key in colors if key.startswith("ink_")}
    tool_values = {value.lower() for key, value in colors.items() if not key.startswith("ink_")}
    for rule in re.findall(r"([^{}]+)\{([^{}]*)\}", sheet):
        selectors, body = rule
        used = {color.lower() for color in re.findall(r"#[0-9a-fA-F]{6}\b", body)}
        if used & (ink_values - tool_values):
            for selector in selectors.split(","):
                assert 'inkStyle="true"' in selector, selector.strip()


def test_the_rounded_typeface_ships_and_is_left_out_for_simplified_chinese():
    from frontengine.ui.style.tokens import INK_FONT
    from frontengine.utils.multi_language.language_wrapper import language_wrapper
    fonts = sorted(app_style.FONTS.glob("*.ttf"))
    assert fonts and sorted(app_style.FONTS.glob("LICENSE*.txt"))
    app_style.load_brand_fonts()
    from PySide6.QtGui import QFontDatabase
    assert INK_FONT in QFontDatabase.families()
    from frontengine.utils.multi_language.retranslate import retranslator
    previous = language_wrapper.language
    page = QWidget()
    child = QLineEdit(page)
    try:
        language_wrapper.reset_language("Traditional_Chinese")
        app_style.mark_ink(page)
        assert page.font().families()[0] == INK_FONT
        assert child.font().families()[0] == INK_FONT                  # children inherit it
        language_wrapper.reset_language("Simplified_Chinese")
        retranslator.apply()                                          # what a language switch runs
        assert INK_FONT not in page.font().families()                 # it lacks much of that script
        language_wrapper.reset_language("Traditional_Chinese")
        retranslator.apply()
        assert page.font().families()[0] == INK_FONT
        assert INK_FONT not in app_style.build_stylesheet("light")    # the stylesheet never names it
    finally:
        language_wrapper.reset_language(previous)
        page.close()


def test_pet_pages_and_dialogs_wear_the_ink_look_and_tools_do_not(make_main_window):
    from frontengine.ui.dialog.pet_photo import PetPhotoDialog
    window = make_main_window()
    for page in (window.pet_home_ui, window.pet_setting_ui):
        assert page.property("inkStyle") is True
        assert page.testAttribute(Qt.WidgetAttribute.WA_StyledBackground)
    for page in (window.tools_setting_ui, window.video_setting_ui, window.control_center_ui):
        assert page.property("inkStyle") is not True
    assert PetPhotoDialog.__init__.__code__.co_names.count("mark_ink") == 1
    from frontengine.ui.dialog import pet_customization, pet_wardrobe
    for module, name in ((pet_customization, "PetCustomizationDialog"), (pet_wardrobe, "PetWardrobeDialog")):
        assert "mark_ink" in getattr(module, name).__init__.__code__.co_names


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
