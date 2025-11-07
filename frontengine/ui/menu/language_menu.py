from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMessageBox

from frontengine.user_setting.user_setting_file import user_setting_dict
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper

if TYPE_CHECKING:
    from frontengine.ui.main_ui import FrontEngineMainUI


def build_language_menu(ui_we_want_to_set: FrontEngineMainUI) -> None:
    """
    建立語言選單
    Build the language menu for the main UI
    """
    front_engine_logger.info(f"[LanguageMenu] build_language_menu | ui={ui_we_want_to_set}")

    language_menu = ui_we_want_to_set.menu_bar.addMenu(
        language_wrapper.language_word_dict.get("menu_bar_language")
    )
    ui_we_want_to_set.language_menu = language_menu

    # 語言清單 (label_key, 語言代碼)
    languages = [
        ("language_menu_bar_english", "English"),
        ("language_menu_bar_traditional_chinese", "Traditional_Chinese"),
        ("language_menu_bar_simplified_chinese", "Simplified_Chinese"),
        ("language_menu_bar_germany", "Deutsch"),
        ("language_menu_bar_russian", "Russian"),
        ("language_menu_bar_french", "French"),
        ("language_menu_bar_italian", "Italian"),
    ]

    # 動態建立 QAction
    for label_key, lang_code in languages:
        action = QAction(language_wrapper.language_word_dict.get(label_key), language_menu)
        action.triggered.connect(lambda _, code=lang_code: set_language(code, ui_we_want_to_set))
        language_menu.addAction(action)


def set_language(language: str, ui_we_want_to_set: FrontEngineMainUI) -> None:
    """
    設定語言並提示使用者重新啟動
    Set application language and prompt user to restart
    """
    front_engine_logger.info(f"[LanguageMenu] set_language | ui={ui_we_want_to_set}, language={language}")
    language_wrapper.reset_language(language)
    user_setting_dict.update({"language": language})

    message_box = QMessageBox(ui_we_want_to_set)
    message_box.setText(language_wrapper.language_word_dict.get("language_menu_bar_please_restart_messagebox"))
    message_box.exec()  # 使用 exec() 讓使用者必須確認
