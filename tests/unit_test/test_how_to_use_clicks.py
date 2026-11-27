"""The quick start names every kind of overlay that takes the mouse (code review CR-02)."""
from frontengine.ui.dialog.how_to_use_dialog import SECTIONS
from frontengine.utils.multi_language.english import english_word_dict


def test_the_click_text_names_scenes_and_sticky_notes():
    body = english_word_dict["how_to_use_clicks_body"]
    for overlay in ("the pet", "drawing layer", "sticky notes", "scenes"):
        assert overlay in body
    assert english_word_dict["control_center_lock_all"] in body


def test_the_dialog_fallback_matches_the_english_dictionary():
    fallback = next(section[3] for section in SECTIONS if section[2] == "how_to_use_clicks_body")
    assert fallback == english_word_dict["how_to_use_clicks_body"]
