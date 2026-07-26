"""
翻譯完整性測試。

會有這支測試，是因為英文與繁體中文一路加到 529 個鍵時，其餘五種語言還停在
125 個 —— 少了 406 個。多數地方有英文備援所以看起來「只是沒翻譯」，但有一個
鍵是用沒有備援的方式取用的，訊息框就直接顯示 "None"。這裡把三件事釘住：
鍵要一致、值不能是空的、`{...}` 佔位符要原封不動。

Translation completeness.

This exists because English and Traditional Chinese grew to 529 keys while the
other five languages sat at 125 - 406 short. Most lookups have an English
fallback, so it merely looked untranslated; but one key is read without a
fallback, and that message box showed the word "None". Three things are pinned
here: the key sets match, no value is blank, and the `{...}` placeholders
survive translation.
"""
import re
from pathlib import Path
from typing import Dict, List

import pytest

from frontengine.utils.multi_language.english import english_word_dict
from frontengine.utils.multi_language.france import french_word_dict
from frontengine.utils.multi_language.germany import germany_word_dict
from frontengine.utils.multi_language.italy import italian_word_dict
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.russian import russian_word_dict
from frontengine.utils.multi_language.simplified_chinese import simplified_chinese_word_dict
from frontengine.utils.multi_language.traditional_chinese import traditional_chinese_word_dict

TRANSLATIONS: Dict[str, dict] = {
    "traditional_chinese": traditional_chinese_word_dict,
    "simplified_chinese": simplified_chinese_word_dict,
    "germany": germany_word_dict,
    "russian": russian_word_dict,
    "france": french_word_dict,
    "italy": italian_word_dict,
}
PLACEHOLDER = re.compile(r"\{[a-z_]+\}")


def _source_files() -> List[Path]:
    return list((Path(__file__).resolve().parents[2] / "frontengine").rglob("*.py"))


@pytest.mark.parametrize("name", sorted(TRANSLATIONS))
def test_every_language_covers_every_english_key(name: str) -> None:
    missing = sorted(set(english_word_dict) - set(TRANSLATIONS[name]))
    assert not missing, f"{name} is missing {len(missing)} keys, e.g. {missing[:5]}"


@pytest.mark.parametrize("name", sorted(TRANSLATIONS))
def test_no_language_carries_a_key_english_dropped(name: str) -> None:
    """
    英文改了鍵名而其他語言沒跟上，就會留下一個沒人讀的孤兒，
    同時在該讀的地方留下一個洞。
    A key renamed in English but not elsewhere leaves an orphan nobody reads -
    and a hole where it should have been read.
    """
    extra = sorted(set(TRANSLATIONS[name]) - set(english_word_dict))
    assert not extra, f"{name} has keys English does not: {extra}"


@pytest.mark.parametrize("name", sorted(TRANSLATIONS))
def test_nothing_is_left_blank(name: str) -> None:
    blank = sorted(key for key, value in TRANSLATIONS[name].items() if not str(value).strip())
    assert not blank, f"{name} has blank values: {blank[:5]}"


@pytest.mark.parametrize("name", sorted(TRANSLATIONS))
def test_placeholders_survive_translation(name: str) -> None:
    """
    `{count}`、`{name}` 這些會被 format 填值。翻掉或翻錯就是 KeyError，
    或是使用者看到一個空格。
    `{count}`, `{name}` and friends get filled in by format. Translate one away
    and it is a KeyError, or a gap where a number should be.
    """
    wrong = []
    for key, value in TRANSLATIONS[name].items():
        expected = set(PLACEHOLDER.findall(str(english_word_dict[key])))
        actual = set(PLACEHOLDER.findall(str(value)))
        if expected != actual:
            wrong.append((key, sorted(expected), sorted(actual)))
    assert not wrong, f"{name} placeholder mismatch: {wrong[:3]}"


def test_keys_read_without_a_fallback_exist_in_every_language() -> None:
    """
    `...get("key")` 沒有第二個參數，缺鍵時回傳 None，畫面上就是 "None"。
    這正是 paint_gif_message_box_text 當初發生的事。
    `...get("key")` with no second argument returns None when the key is
    absent, and the UI shows the word "None" - which is exactly what
    paint_gif_message_box_text did.
    """
    pattern = re.compile(r'language_word_dict\.get\("([a-z0-9_]+)"\)')
    required = set()
    for path in _source_files():
        required.update(pattern.findall(path.read_text(encoding="utf-8")))
    assert required, "no fallback-free lookups found - has the pattern changed?"

    holes = {name: sorted(required - set(words)) for name, words in TRANSLATIONS.items()}
    holes = {name: keys for name, keys in holes.items() if keys}
    assert not holes, f"these would render as 'None': {holes}"


def test_every_registered_language_is_complete() -> None:
    """語言選單上列得出來的，就必須是翻得完整的。"""
    for label, words in language_wrapper.choose_language_dict.items():
        missing = set(english_word_dict) - set(words)
        assert not missing, f"{label} is offered in the menu but misses {len(missing)} keys"


def test_the_menu_offers_exactly_the_languages_that_exist() -> None:
    assert set(language_wrapper.choose_language_dict) == {
        "English", "Traditional_Chinese", "Simplified_Chinese", "Deutsch",
        "Russian", "France", "Italy",
    }
