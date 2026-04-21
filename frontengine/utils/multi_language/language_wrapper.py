from typing import Dict

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

    def reset_language(self, language: str) -> None:
        word_dict = self.choose_language_dict.get(language)
        if word_dict is None:
            return
        self.language = language
        self.language_word_dict = word_dict


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
