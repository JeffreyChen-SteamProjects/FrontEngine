"""
創意工坊內容辨識與外掛載入的測試：全部用暫存資料夾，不碰真的 Steam 也不裝外掛。
Tests for Workshop content recognition and plugin loading — all against
temporary folders, touching neither a real Steam install nor a real plugin.
"""
from frontengine.utils.plugins.plugin_loader import (
    ENTRY_NAME, discover_plugins, load_plugins, module_name_for, register_plugin_tabs,
)
from frontengine.utils.workshop.workshop_content import (
    APP_ID, KIND_MEDIA, KIND_PET_PACK, KIND_PRESET, classify_item, default_library_paths,
    find_workshop_dir, preset_files, read_item_title, scan_workshop_items, workshop_content_dir,
)


def make_workshop(tmp_path):
    """搭一個假的 Steam 目錄結構 / Build a fake Steam layout."""
    content = tmp_path / "steamapps" / "workshop" / "content" / APP_ID
    content.mkdir(parents=True)
    return content


# --- workshop discovery ---------------------------------------------------
def test_content_dir_found_under_a_steam_path(tmp_path) -> None:
    content = make_workshop(tmp_path)
    assert workshop_content_dir(tmp_path) == content


def test_content_dir_missing(tmp_path) -> None:
    assert workshop_content_dir(tmp_path) is None
    assert workshop_content_dir(None) is None


def test_find_workshop_dir_accepts_an_explicit_path(tmp_path) -> None:
    content = make_workshop(tmp_path)
    assert find_workshop_dir(extra_paths=[str(tmp_path)]) == content


def test_default_library_paths_are_absolute() -> None:
    paths = default_library_paths()
    assert paths and all(path.is_absolute() for path in paths)


# --- item classification --------------------------------------------------
def test_a_folder_with_state_sprites_is_a_pet_pack(tmp_path) -> None:
    item = tmp_path / "123"
    item.mkdir()
    (item / "walk.png").write_bytes(b"x")
    (item / "idle.png").write_bytes(b"x")
    assert classify_item(item) == KIND_PET_PACK


def test_a_folder_with_a_manifest_is_a_pet_pack(tmp_path) -> None:
    item = tmp_path / "124"
    item.mkdir()
    (item / "pet.json").write_text('{"name": "Mochi"}', encoding="utf-8")
    assert classify_item(item) == KIND_PET_PACK
    assert read_item_title(item) == "Mochi"


def test_a_folder_with_json_is_a_preset(tmp_path) -> None:
    item = tmp_path / "125"
    item.mkdir()
    (item / "my_scene.json").write_text("{}", encoding="utf-8")
    assert classify_item(item) == KIND_PRESET
    assert preset_files(item) == [str(item / "my_scene.json")]


def test_a_folder_of_pictures_is_media(tmp_path) -> None:
    item = tmp_path / "126"
    item.mkdir()
    (item / "art.png").write_bytes(b"x")
    assert classify_item(item) == KIND_MEDIA


def test_unrecognisable_items_are_skipped(tmp_path) -> None:
    item = tmp_path / "127"
    item.mkdir()
    (item / "readme.md").write_text("hello", encoding="utf-8")
    assert classify_item(item) is None
    assert classify_item(tmp_path / "missing") is None


def test_title_falls_back_to_the_item_id(tmp_path) -> None:
    item = tmp_path / "999"
    item.mkdir()
    assert read_item_title(item) == "999"


def test_a_broken_manifest_does_not_break_the_title(tmp_path) -> None:
    item = tmp_path / "998"
    item.mkdir()
    (item / "pet.json").write_text("{not json", encoding="utf-8")
    assert read_item_title(item) == "998"


def test_scanning_lists_recognised_items(tmp_path) -> None:
    content = make_workshop(tmp_path)
    pack = content / "111"
    pack.mkdir()
    (pack / "walk.gif").write_bytes(b"x")
    preset = content / "222"
    preset.mkdir()
    (preset / "scene.json").write_text("{}", encoding="utf-8")
    junk = content / "333"
    junk.mkdir()
    (junk / "notes.md").write_text("x", encoding="utf-8")

    items = scan_workshop_items(content)
    kinds = {item["id"]: item["kind"] for item in items}
    assert kinds == {"111": KIND_PET_PACK, "222": KIND_PRESET}
    assert all(item["path"] for item in items)


def test_scanning_a_missing_folder(tmp_path) -> None:
    assert scan_workshop_items(tmp_path / "nope") == []


# --- plugins --------------------------------------------------------------
def test_plugins_are_not_loaded_unless_enabled(tmp_path) -> None:
    (tmp_path / "boom.py").write_text("raise RuntimeError('should never run')", encoding="utf-8")
    registry = {}
    assert load_plugins(registry, enabled=False, base=str(tmp_path)) == []
    assert registry == {}, "disabled means nothing is imported at all"


def test_discovery_finds_both_layouts(tmp_path) -> None:
    (tmp_path / "single.py").write_text("", encoding="utf-8")
    package = tmp_path / "bundled"
    package.mkdir()
    (package / ENTRY_NAME).write_text("", encoding="utf-8")
    (tmp_path / "_private.py").write_text("", encoding="utf-8")
    found = {path.name for path in discover_plugins(str(tmp_path))}
    assert found == {"single.py", ENTRY_NAME}, "underscore files are skipped"


def test_discovery_on_a_missing_folder(tmp_path) -> None:
    assert discover_plugins(str(tmp_path / "nope")) == []


def test_module_names_are_namespaced(tmp_path) -> None:
    assert module_name_for(tmp_path / "cool.py").startswith("frontengine_plugin_")
    assert module_name_for(tmp_path / "bundled" / ENTRY_NAME).endswith("bundled")


def test_a_plugin_can_register_tabs(tmp_path) -> None:
    (tmp_path / "tabs.py").write_text(
        "class Widget:\n    pass\n\nFRONTENGINE_TABS = {'Demo': Widget}\n", encoding="utf-8")
    registry = {}
    assert load_plugins(registry, enabled=True, base=str(tmp_path)) == ["Demo"]
    assert "Demo" in registry


def test_a_plugin_can_use_a_register_function(tmp_path) -> None:
    (tmp_path / "hook.py").write_text(
        "class Widget:\n    pass\n\ndef register(registry):\n    registry['Hooked'] = Widget\n",
        encoding="utf-8")
    registry = {}
    assert load_plugins(registry, enabled=True, base=str(tmp_path)) == ["Hooked"]


def test_one_broken_plugin_does_not_stop_the_others(tmp_path) -> None:
    (tmp_path / "a_broken.py").write_text("raise RuntimeError('bad plugin')", encoding="utf-8")
    (tmp_path / "b_good.py").write_text(
        "class Widget:\n    pass\n\nFRONTENGINE_TABS = {'Good': Widget}\n", encoding="utf-8")
    registry = {}
    assert load_plugins(registry, enabled=True, base=str(tmp_path)) == ["Good"]


def test_malformed_tab_declarations_are_ignored(tmp_path) -> None:
    registry = {}

    class Module:
        FRONTENGINE_TABS = {"ok": type("W", (), {}), 5: "nope", "bad": "not a class"}

    assert register_plugin_tabs(Module(), registry) == ["ok"]
    assert register_plugin_tabs(None, registry) == []


def test_a_failing_register_function_is_contained(tmp_path) -> None:
    class Module:
        @staticmethod
        def register(_registry):
            raise RuntimeError("bad hook")

    assert register_plugin_tabs(Module(), {}) == []
