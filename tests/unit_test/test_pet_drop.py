"""
拖曳到寵物身上的檔案判斷測試（純邏輯，不建立 widget）。
Tests for files dropped onto the pet - pure logic, no widgets. Pets are layered only, so a
dropped picture is food like any other file; it never changes the pet's look.
"""
from frontengine.show.pet.desktop_pet import droppable_food


def test_any_existing_file_is_food_pictures_included(tmp_path) -> None:
    for name in ("notes.txt", "sprite.png", "SPRITE.GIF", "walk.webp", "song.mp3"):
        dropped = tmp_path / name
        dropped.write_bytes(b"x")
        assert droppable_food(str(dropped)), name


def test_folders_are_not_eaten_even_old_sprite_packs(tmp_path) -> None:
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "walk.png").write_bytes(b"x")
    assert not droppable_food(str(pack))


def test_unusable_paths_are_ignored(tmp_path) -> None:
    assert not droppable_food(str(tmp_path / "missing.png"))
    assert not droppable_food(None)
    assert not droppable_food("\0not-a-path")
