"""Layout kit after the redesign: one centred column, header actions, even controls, calm headings."""
import re

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication, QComboBox, QPushButton

from frontengine.ui.page.action_menu import ActionMenu
from frontengine.ui.page.layout_kit import CONTENT_MAX_WIDTH, SettingPage
from frontengine.ui.style.app_style import apply_app_style, build_palette
from frontengine.ui.style.tokens import DARK, LIGHT
from frontengine.utils.multi_language.english import english_word_dict
from frontengine.utils.multi_language.france import french_word_dict
from frontengine.utils.multi_language.germany import germany_word_dict
from frontengine.utils.multi_language.italy import italian_word_dict
from frontengine.utils.multi_language.russian import russian_word_dict


def _page(wide=False):
    page = SettingPage("tab_video_text", "page_subtitle_video", "Video", "", wide=wide)
    section = page.add_section("section_source", "Source")
    section.add_row("section_where", QComboBox(), "Where")
    page.finish_body()
    apply_app_style(page, "light")
    page.resize(1600, 700)
    page.show()
    QCoreApplication.processEvents()
    return page, section


def test_sections_stay_in_one_centred_column_on_a_wide_window():
    page, section = _page()
    assert section.width() <= CONTENT_MAX_WIDTH
    left = section.mapTo(page, section.rect().topLeft()).x()
    right = page.width() - (left + section.width())
    assert abs(left - right) <= 16                     # centred (the scroll bar may take a few pixels)
    title = page.title_label.mapTo(page, page.title_label.rect().topLeft()).x()
    assert abs(title - left) <= 2                      # the title lines up with the cards
    page.close()


def test_wide_pages_use_the_whole_width():
    page, section = _page(wide=True)
    assert section.width() > CONTENT_MAX_WIDTH
    page.close()


def test_header_actions_sit_beside_the_title():
    page = SettingPage("tab_video_text", "page_subtitle_video", "Video")
    button = page.add_header_action(QPushButton("Help"))
    page.resize(1200, 500)
    page.show()
    QCoreApplication.processEvents()
    assert button.isVisible()
    assert button.mapTo(page, button.rect().topLeft()).x() > page.title_label.mapTo(page, page.title_label.rect().topLeft()).x() + 200
    page.close()


def test_menu_buttons_are_as_tall_as_ordinary_buttons():
    page, section = _page()
    plain, extra = QPushButton("Choose"), QPushButton("Other")
    holder = section.add_actions(plain, extra)
    QCoreApplication.processEvents()
    menu = holder.findChild(ActionMenu)
    assert abs(menu.height() - plain.height()) <= 1
    page.close()


@pytest.mark.parametrize("words", [english_word_dict, germany_word_dict, russian_word_dict, french_word_dict,
                                   italian_word_dict])
def test_section_headings_are_not_shouted(words):
    loud = [key for key, value in words.items()
            if re.fullmatch(r"section_[a-z_]+", key) and len(value) > 2 and value.isupper()]
    assert not loud


def test_the_main_window_theme_reaches_self_painted_widgets():
    before = QGuiApplication.palette()
    try:
        from PySide6.QtWidgets import QWidget
        window = QWidget()
        apply_app_style(window, "dark", application=True)
        assert QApplication.palette().color(QPalette.ColorRole.Base).name().lower() == DARK["input"].lower()
        apply_app_style(window, "light", application=True)
        assert QApplication.palette().color(QPalette.ColorRole.Base).name().lower() == LIGHT["input"].lower()
        assert build_palette("light").color(QPalette.ColorRole.Mid).name().lower() == LIGHT["border"].lower()
    finally:
        QGuiApplication.setPalette(before)
