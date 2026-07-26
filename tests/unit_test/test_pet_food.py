"""
食物種類判斷與效果表的測試（純邏輯，不建立 widget）。
Tests for food classification and the effect table — pure logic, no widgets.
"""
from frontengine.show.pet.desktop_pet import (
    FOOD_BOOK, FOOD_EFFECTS, FOOD_FEAST, FOOD_HARD, FOOD_MUSIC, FOOD_SNACK, acceptable_sound,
    classify_food,
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


# --- pet sound paths come from outside data -------------------------------
def test_only_an_existing_audio_file_is_accepted_as_a_pet_sound(tmp_path) -> None:
    """
    音效路徑可能來自匯入的預設集或 Workshop 內容，所以不是音訊檔就不該載入。
    The sound path can arrive from an imported preset or Workshop content, so
    anything that is not an audio file must not be loaded.
    """
    sound = tmp_path / "bark.wav"
    sound.write_bytes(b"RIFF....WAVEfmt ")
    document = tmp_path / "secrets.txt"
    document.write_text("not a sound", encoding="utf-8")

    assert acceptable_sound(str(sound)) == sound
    assert acceptable_sound(str(document)) is None
    assert acceptable_sound(str(tmp_path / "gone.wav")) is None
    assert acceptable_sound(str(tmp_path)) is None
    assert acceptable_sound("") is None
    assert acceptable_sound(None) is None
