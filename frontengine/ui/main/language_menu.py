from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QMessageBox

from frontengine.utils.multi_language.language_wrapper import language_wrapper


def build_language_menu(ui_we_want_to_set: QMainWindow):
    ui_we_want_to_set.menu_bar.language_menu = ui_we_want_to_set.menu_bar.addMenu(
        language_wrapper.language_word_dict.get("menu_bar_language")
    )
    ui_we_want_to_set.menu_bar.language_menu.change_to_english_language_action = QAction(
        language_wrapper.language_word_dict.get("language_menu_bar_english")
    )
    ui_we_want_to_set.menu_bar.language_menu.change_to_english_language_action.triggered.connect(
        lambda: set_language("English", ui_we_want_to_set)
    )
    ui_we_want_to_set.menu_bar.language_menu.change_to_traditional_chinese_language_action = QAction(
        language_wrapper.language_word_dict.get("language_menu_bar_traditional_chinese")
    )
    ui_we_want_to_set.menu_bar.language_menu.change_to_traditional_chinese_language_action.triggered.connect(
        lambda: set_language("Traditional_Chinese", ui_we_want_to_set)
    )
    ui_we_want_to_set.menu_bar.language_menu.addAction(
        ui_we_want_to_set.menu_bar.language_menu.change_to_english_language_action
    )
    ui_we_want_to_set.menu_bar.language_menu.addAction(
        ui_we_want_to_set.menu_bar.language_menu.change_to_traditional_chinese_language_action
    )


def set_language(language: str, ui_we_want_to_set: QMainWindow):
    language_wrapper.reset_language(language)
    message_box = QMessageBox(ui_we_want_to_set)
    message_box.setText(language_wrapper.language_word_dict.get("language_menu_bar_please_restart_messagebox"))
    message_box.show()
