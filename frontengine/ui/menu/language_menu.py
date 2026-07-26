from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple

from PySide6.QtGui import QAction

from frontengine.user_setting.user_setting_file import user_setting_dict
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import retranslator, translate

if TYPE_CHECKING:
    from frontengine.ui.main_ui import FrontEngineMainUI

# (顯示用的鍵, 語言代碼)。代碼必須是 language_wrapper 註冊過的名字——這裡原本寫
# "French" / "Italian"，而註冊的是 "France" / "Italy"，reset_language() 找不到就
# 默默 return，所以那兩個選項按下去完全沒有反應。
# (label key, language code). The code must be a name language_wrapper
# registered: this list used to say "French" / "Italian" while the registry
# said "France" / "Italy", and reset_language() returns quietly on a name it
# does not know - so those two entries did nothing at all.
LANGUAGES: List[Tuple[str, str]] = [
    ("language_menu_bar_english", "English"),
    ("language_menu_bar_traditional_chinese", "Traditional_Chinese"),
    ("language_menu_bar_simplified_chinese", "Simplified_Chinese"),
    ("language_menu_bar_germany", "Deutsch"),
    ("language_menu_bar_russian", "Russian"),
    ("language_menu_bar_french", "France"),
    ("language_menu_bar_italian", "Italy"),
]


def build_language_menu(ui_we_want_to_set: FrontEngineMainUI) -> None:
    """
    建立語言選單
    Build the language menu for the main UI
    """
    front_engine_logger.info(f"[LanguageMenu] build_language_menu | ui={ui_we_want_to_set}")

    language_menu = ui_we_want_to_set.menu_bar.addMenu(translate("menu_bar_language", "Language"))
    retranslator.bind(language_menu, "menu_bar_language", "Language", "setTitle")
    ui_we_want_to_set.language_menu = language_menu

    for label_key, language_code in LANGUAGES:
        action = QAction(translate(label_key, language_code), language_menu)
        retranslator.bind(action, label_key, language_code)
        action.triggered.connect(
            lambda _, code=language_code: set_language(code, ui_we_want_to_set))
        language_menu.addAction(action)


def set_language(language: str, ui_we_want_to_set: FrontEngineMainUI) -> bool:
    """
    切換語言並立刻重寫畫面上的文字，不必重新啟動。
    回傳是否真的換成功（語言代碼不認得就是 False）。
    Switch language and rewrite the interface immediately - no restart needed.
    Returns whether the switch actually happened; an unknown code gives False.
    """
    front_engine_logger.info(f"[LanguageMenu] set_language | language={language}")
    if not language_wrapper.reset_language(language):
        return False
    user_setting_dict.update({"language": language})
    ui_we_want_to_set.retranslate()
    return True
