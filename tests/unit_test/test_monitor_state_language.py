import json

import pytest

from frontengine.ui.page.utils import build_target_monitor_combobox
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import retranslator


PAGES = (
    "text", "image", "video", "gif", "web", "particle", "pet",
    "focus", "presentation", "screen_care",
)


def test_all_monitor_presets_survive_language_changes(make_main_window):
    window = make_main_window({"language": "English"})
    try:
        for name in PAGES:
            page = getattr(window, name + "_setting_ui")
            page.target_monitor_combobox = build_target_monitor_combobox(screens=[object(), object()])
            combo = page.target_monitor_combobox
            for index, expected in enumerate(("here", "0", "1", "span")):
                combo.setCurrentIndex(index)
                saved = json.loads(json.dumps(page.get_state()))
                assert saved["target_monitor"] == expected, name
                for language in language_wrapper.choose_language_dict:
                    language_wrapper.reset_language(language)
                    retranslator.apply()
                    assert page.get_state()["target_monitor"] == expected, (name, language)
                    combo.setCurrentIndex((index + 1) % combo.count())
                    page.set_state(saved)
                    assert combo.currentIndex() == index, (name, language, expected)
            for words in language_wrapper.choose_language_dict.values():
                for key, index in (("target_monitor_here", 0), ("target_monitor_span", 3)):
                    combo.setCurrentIndex(2)
                    page.set_state({"target_monitor": words[key]})
                    assert combo.currentIndex() == index, (name, key)
            combo.close()
    finally:
        language_wrapper.reset_language("English")
        retranslator.apply()
        window.close()


@pytest.mark.parametrize("value", [None, "", "unknown", "-1", "99", True, [], {}, 1.5, "span"])
def test_invalid_or_unavailable_monitor_keeps_selection(value, make_main_window):
    window = make_main_window({"language": "English"})
    page = window.text_setting_ui
    page.target_monitor_combobox = build_target_monitor_combobox(screens=[object()])
    page.target_monitor_combobox.setCurrentIndex(1)
    try:
        page.set_state({"target_monitor": value})
        assert page.target_monitor_combobox.currentIndex() == 1
        page.set_state({})
        assert page.target_monitor_combobox.currentIndex() == 1
    finally:
        page.target_monitor_combobox.close()
        window.close()
