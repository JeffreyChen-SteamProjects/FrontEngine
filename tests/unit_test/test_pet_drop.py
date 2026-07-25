"""
拖曳到寵物身上的檔案判斷測試（純邏輯，不建立 widget）。
Tests for classifying files dropped onto the pet — pure logic, no widgets.
"""
from frontengine.show.pet.desktop_pet import DROP_FOOD, DROP_SPRITE, classify_drop


def test_images_are_worn(tmp_path) -> None:
    for suffix in (".png", ".gif", ".webp", ".jpg", ".jpeg"):
        image = tmp_path / f"sprite{suffix}"
        image.write_bytes(b"x")
        assert classify_drop(str(image)) == DROP_SPRITE


def test_suffix_case_is_ignored(tmp_path) -> None:
    image = tmp_path / "SPRITE.PNG"
    image.write_bytes(b"x")
    assert classify_drop(str(image)) == DROP_SPRITE


def test_other_files_are_food(tmp_path) -> None:
    snack = tmp_path / "notes.txt"
    snack.write_text("nom")
    assert classify_drop(str(snack)) == DROP_FOOD


def test_a_pack_folder_is_worn(tmp_path) -> None:
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "walk.png").write_bytes(b"x")
    assert classify_drop(str(pack)) == DROP_SPRITE


def test_a_folder_without_sprites_is_ignored(tmp_path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    assert classify_drop(str(empty)) is None


def test_unusable_paths_are_ignored(tmp_path) -> None:
    assert classify_drop(str(tmp_path / "missing.png")) is None
    assert classify_drop(None) is None
    assert classify_drop("\0not-a-path") is None
