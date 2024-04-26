from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from frontengine.ui.main_ui import FrontEngineMainUI
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMessageBox

from frontengine.user_setting.user_setting_file import user_setting_dict
from frontengine.utils.multi_language.language_wrapper import language_wrapper


def build_language_menu(ui_we_want_to_set: FrontEngineMainUI) -> None:
    ui_we_want_to_set.language_menu = ui_we_want_to_set.menu_bar.addMenu(
        language_wrapper.language_word_dict.get("menu_bar_language")
    )
    ui_we_want_to_set.language_menu.change_to_english_language_action = QAction(
        language_wrapper.language_word_dict.get("language_menu_bar_english")
    )
    ui_we_want_to_set.language_menu.change_to_english_language_action.triggered.connect(
        lambda: set_language("English", ui_we_want_to_set)
    )
    ui_we_want_to_set.language_menu.change_to_traditional_chinese_language_action = QAction(
        language_wrapper.language_word_dict.get("language_menu_bar_traditional_chinese")
    )
    ui_we_want_to_set.language_menu.change_to_traditional_chinese_language_action.triggered.connect(
        lambda: set_language("Traditional_Chinese", ui_we_want_to_set)
    )
    ui_we_want_to_set.language_menu.change_to_simplified_chinese_language_action = QAction(
        language_wrapper.language_word_dict.get("language_menu_bar_simplified_chinese")
    )
    ui_we_want_to_set.language_menu.change_to_simplified_chinese_language_action.triggered.connect(
        lambda: set_language("Simplified_Chinese", ui_we_want_to_set)
    )
    ui_we_want_to_set.language_menu.change_to_deutsch_language_action = QAction(
        language_wrapper.language_word_dict.get("language_menu_bar_germany")
    )
    ui_we_want_to_set.language_menu.change_to_deutsch_language_action.triggered.connect(
        lambda: set_language("Deutsch", ui_we_want_to_set)
    )
    ui_we_want_to_set.language_menu.change_to_russian_language_action = QAction(
        language_wrapper.language_word_dict.get("language_menu_bar_russian")
    )
    ui_we_want_to_set.language_menu.change_to_russian_language_action.triggered.connect(
        lambda: set_language("Russian", ui_we_want_to_set)
    )
    ui_we_want_to_set.language_menu.change_to_france_language_action = QAction(
        language_wrapper.language_word_dict.get("language_menu_bar_french")
    )
    ui_we_want_to_set.language_menu.change_to_france_language_action.triggered.connect(
        lambda: set_language("France", ui_we_want_to_set)
    )
    ui_we_want_to_set.language_menu.change_to_italian_language_action = QAction(
        language_wrapper.language_word_dict.get("language_menu_bar_italian")
    )
    ui_we_want_to_set.language_menu.change_to_italian_language_action.triggered.connect(
        lambda: set_language("Italy", ui_we_want_to_set)
    )
    ui_we_want_to_set.language_menu.addAction(
        ui_we_want_to_set.language_menu.change_to_english_language_action
    )
    ui_we_want_to_set.language_menu.addAction(
        ui_we_want_to_set.language_menu.change_to_traditional_chinese_language_action
    )
    ui_we_want_to_set.language_menu.addAction(
        ui_we_want_to_set.language_menu.change_to_simplified_chinese_language_action
    )
    ui_we_want_to_set.language_menu.addAction(
        ui_we_want_to_set.language_menu.change_to_deutsch_language_action
    )
    ui_we_want_to_set.language_menu.addAction(
        ui_we_want_to_set.language_menu.change_to_russian_language_action
    )
    ui_we_want_to_set.language_menu.addAction(
        ui_we_want_to_set.language_menu.change_to_france_language_action
    )
    ui_we_want_to_set.language_menu.addAction(
        ui_we_want_to_set.language_menu.change_to_italian_language_action
    )


def set_language(language: str, ui_we_want_to_set: FrontEngineMainUI) -> None:
    language_wrapper.reset_language(language)
    user_setting_dict.update({"language": language})
    message_box = QMessageBox(ui_we_want_to_set)
    message_box.setText(language_wrapper.language_word_dict.get("language_menu_bar_please_restart_messagebox"))
    message_box.show()
