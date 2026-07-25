"""
食物種類判斷與效果表的測試（純邏輯，不建立 widget）。
Tests for food classification and the effect table — pure logic, no widgets.
"""
from frontengine.show.pet.desktop_pet import (
    FOOD_BOOK, FOOD_EFFECTS, FOOD_FEAST, FOOD_HARD, FOOD_MUSIC, FOOD_SNACK, classify_food,
)


def test_archives_are_a_feast() -> None:
    assert classify_food("backup.zip") == FOOD_FEAST
    assert classify_food("game.7z") == FOOD_FEAST
    assert classify_food("disk.iso") == FOOD_FEAST


def test_audio_is_music() -> None:
    assert classify_food("song.mp3") == FOOD_MUSIC
    assert classify_food("effect.wav") == FOOD_MUSIC
    assert classify_food("album.flac") == FOOD_MUSIC


def test_documents_are_books() -> None:
    assert classify_food("notes.txt") == FOOD_BOOK
    assert classify_food("manual.pdf") == FOOD_BOOK
    assert classify_food("report.docx") == FOOD_BOOK


def test_binaries_are_too_hard() -> None:
    assert classify_food("setup.exe") == FOOD_HARD
    assert classify_food("driver.sys") == FOOD_HARD


def test_unknown_and_unusable_paths_are_plain_snacks() -> None:
    assert classify_food("mystery.qqq") == FOOD_SNACK
    assert classify_food("no_suffix") == FOOD_SNACK
    assert classify_food(None) == FOOD_SNACK
    assert classify_food("\0bad") == FOOD_SNACK


def test_suffix_case_is_ignored() -> None:
    assert classify_food("SONG.MP3") == FOOD_MUSIC
    assert classify_food("Backup.ZIP") == FOOD_FEAST


def test_every_kind_has_a_complete_effect() -> None:
    for kind in (FOOD_SNACK, FOOD_FEAST, FOOD_MUSIC, FOOD_BOOK, FOOD_HARD):
        effect = FOOD_EFFECTS[kind]
        assert set(effect) == {"fullness", "mood", "affection"}
        assert effect["fullness"] >= 0
        assert effect["affection"] >= 0


def test_the_kinds_actually_differ() -> None:
    assert FOOD_EFFECTS[FOOD_FEAST]["fullness"] > FOOD_EFFECTS[FOOD_SNACK]["fullness"]
    assert FOOD_EFFECTS[FOOD_MUSIC]["mood"] > FOOD_EFFECTS[FOOD_SNACK]["mood"]
    assert FOOD_EFFECTS[FOOD_MUSIC]["fullness"] < FOOD_EFFECTS[FOOD_SNACK]["fullness"]
    assert FOOD_EFFECTS[FOOD_HARD]["mood"] < 0, "a binary should not be enjoyed"
