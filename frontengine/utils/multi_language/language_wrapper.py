from typing import Dict

from frontengine.utils.logging.loggin_instance import front_engine_logger

from frontengine.utils.multi_language.english import english_word_dict
from frontengine.utils.multi_language.france import french_word_dict
from frontengine.utils.multi_language.germany import germany_word_dict
from frontengine.utils.multi_language.italy import italian_word_dict
from frontengine.utils.multi_language.russian import russian_word_dict
from frontengine.utils.multi_language.simplified_chinese import simplified_chinese_word_dict
from frontengine.utils.multi_language.traditional_chinese import traditional_chinese_word_dict


class LanguageWrapper:
    """
    Registry-backed language wrapper. Add a new language with `register`;
    the registry is the single source of truth, so there is no whitelist
    to keep in sync with the dictionary keys.
    """

    DEFAULT_LANGUAGE: str = "English"

    def __init__(self) -> None:
        self.choose_language_dict: Dict[str, dict] = {}
        self.language: str = self.DEFAULT_LANGUAGE
        self.language_word_dict: dict = {}

    def register(self, name: str, word_dict: dict) -> None:
        self.choose_language_dict[name] = word_dict
        if name == self.language:
            self.language_word_dict = word_dict

    def reset_language(self, language: str) -> bool:
        """
        切換語言，回傳是否切換成功。

        以前這裡遇到不認得的名字就直接 return，錯字不會有任何痕跡——選單上的
        「French」和「Italian」送的正是註冊表裡沒有的名字，按下去毫無反應也毫無
        線索。現在會記一筆並回報失敗。

        Switch language, reporting whether it happened. This used to return
        silently on a name it did not know, so a typo left no trace - the menu's
        "French" and "Italian" sent exactly such names and did nothing at all,
        with nothing to show why. Now it logs and says so.
        """
        word_dict = self.choose_language_dict.get(language)
        if word_dict is None:
            front_engine_logger.warning(
                f"[LanguageWrapper] unknown language {language!r}; "
                f"known: {sorted(self.choose_language_dict)}")
            return False
        self.language = language
        self.language_word_dict = word_dict
        return True


language_wrapper = LanguageWrapper()

for _name, _words in (
    ("English", english_word_dict),
    ("Traditional_Chinese", traditional_chinese_word_dict),
    ("Simplified_Chinese", simplified_chinese_word_dict),
    ("Deutsch", germany_word_dict),
    ("Russian", russian_word_dict),
    ("France", french_word_dict),
    ("Italy", italian_word_dict),
):
    language_wrapper.register(_name, _words)

language_wrapper.reset_language(LanguageWrapper.DEFAULT_LANGUAGE)
