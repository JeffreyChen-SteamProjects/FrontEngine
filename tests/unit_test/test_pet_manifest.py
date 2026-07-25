"""
動作包 pet.json 的解析測試：只接受認得且型別正確的欄位，壞掉的包不能弄壞寵物。
Tests for pack manifests: only known, well-typed fields are accepted, and a
broken pack must never break the pet.
"""
import json

from frontengine.show.pet.desktop_pet import PACK_MANIFEST_NAME, read_pet_manifest


def write_manifest(folder, payload) -> str:
    folder.mkdir(exist_ok=True)
    path = folder / PACK_MANIFEST_NAME
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")
    return str(folder)


def test_no_manifest_is_fine(tmp_path) -> None:
    (tmp_path / "pack").mkdir()
    assert read_pet_manifest(str(tmp_path / "pack")) == {}


def test_missing_folder_is_fine(tmp_path) -> None:
    assert read_pet_manifest(str(tmp_path / "nope")) == {}
    assert read_pet_manifest(None) == {}


def test_known_fields_are_read(tmp_path) -> None:
    folder = write_manifest(tmp_path / "pack", {
        "name": "Mochi", "size": 96, "speed": 5, "climb": False, "talk": True,
        "sound": "meow.wav", "lines": {"any": ["hi", "hello"], "morning": ["morning!"]},
    })
    manifest = read_pet_manifest(folder)
    assert manifest["name"] == "Mochi"
    assert manifest["size"] == 96
    assert manifest["speed"] == 5
    assert manifest["climb"] is False
    assert manifest["talk"] is True
    assert manifest["sound"] == "meow.wav"
    assert manifest["lines"] == {"any": ["hi", "hello"], "morning": ["morning!"]}


def test_unknown_fields_are_ignored(tmp_path) -> None:
    folder = write_manifest(tmp_path / "pack", {"size": 64, "eval": "rm -rf /", "extra": {"a": 1}})
    manifest = read_pet_manifest(folder)
    assert set(manifest) == {"size"}


def test_wrong_types_are_skipped(tmp_path) -> None:
    folder = write_manifest(tmp_path / "pack", {
        "size": "big", "speed": None, "climb": "yes", "name": 5, "lines": "not a mapping",
    })
    assert read_pet_manifest(folder) == {}


def test_empty_line_pools_are_dropped(tmp_path) -> None:
    folder = write_manifest(tmp_path / "pack", {"lines": {"any": [], "meet": ["yo"], "bad": "x"}})
    assert read_pet_manifest(folder)["lines"] == {"meet": ["yo"]}


def test_broken_json_is_ignored(tmp_path) -> None:
    folder = write_manifest(tmp_path / "pack", "{not json at all")
    assert read_pet_manifest(folder) == {}


def test_a_json_list_is_ignored(tmp_path) -> None:
    folder = write_manifest(tmp_path / "pack", [1, 2, 3])
    assert read_pet_manifest(folder) == {}


def test_sizes_are_clamped_to_something_usable(tmp_path) -> None:
    folder = write_manifest(tmp_path / "pack", {"size": -50, "speed": 0})
    manifest = read_pet_manifest(folder)
    assert manifest["size"] >= 1 and manifest["speed"] >= 1
