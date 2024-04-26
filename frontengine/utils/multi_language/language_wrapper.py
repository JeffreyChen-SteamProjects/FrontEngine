from frontengine.utils.multi_language.france import french_word_dict
from frontengine.utils.multi_language.germany import germany_word_dict
from frontengine.utils.multi_language.italy import italian_word_dict
from frontengine.utils.multi_language.russian import russian_word_dict
from frontengine.utils.multi_language.simplified_chinese import simplified_chinese_word_dict
from frontengine.utils.multi_language.english import english_word_dict
from frontengine.utils.multi_language.traditional_chinese import traditional_chinese_word_dict


class LanguageWrapper(object):

    def __init__(
            self
    ):
        self.language: str = "English"
        self.choose_language_dict = {
            "English": english_word_dict,
            "Traditional_Chinese": traditional_chinese_word_dict,
            "Simplified_Chinese": simplified_chinese_word_dict,
            "Deutsch": germany_word_dict,
            "Russian": russian_word_dict,
            "France": french_word_dict,
            "Italy": italian_word_dict,
        }
        self.language_word_dict: dict = self.choose_language_dict.get(self.language)

    def reset_language(self, language) -> None:
        if language in [
            "English",
            "Traditional_Chinese",
            "Simplified_Chinese",
            "Deutsch",
            "Russian",
            "France",
            "Italy"
        ]:
            self.language = language
            self.language_word_dict = self.choose_language_dict.get(self.language)


language_wrapper = LanguageWrapper()
