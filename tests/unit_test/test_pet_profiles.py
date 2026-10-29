import copy
import json
from pathlib import Path

import pytest

from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.user_setting.pet_profile_schema import checked_profile
from frontengine.utils.json.json_repository import JsonRepository


def test_profiles_migrate_once_and_survive_reopen_without_overwriting_peers(tmp_path):
    settings = {"pet_mood": 81, "pet_hunger": 32, "pet_affection": 95}
    file = JsonRepository(tmp_path / "settings.json")
    profiles = PetProfiles(settings, lambda: file.save(settings))
    first = profiles.create("Amber")
    second = profiles.create("Blue")
    assert (first["mood"], first["fullness"], first["affection"]) == (81, 32, 95)
    assert (second["mood"], second["fullness"], second["affection"]) == (60, 70, 0)
    profiles.update(first["id"], {"mood": 90, "affection": 100})
    profiles.update(second["id"], {"fullness": 20})
    reopened = PetProfiles(file.load(), lambda: None)
    assert reopened.get(first["id"])["mood"] == 90
    assert reopened.get(second["id"])["fullness"] == 20
    assert reopened.get(second["id"])["affection"] == 0
    detached = reopened.get(first["id"])
    detached["mood"] = 0
    assert reopened.get(first["id"])["mood"] == 90


def test_portable_import_assigns_new_identity_and_preserves_original(tmp_path):
    profiles = PetProfiles({}, lambda: None)
    first = profiles.create("Amber")
    profiles.update(first["id"], {"affection": 200, "fullness": 8})
    export = tmp_path / "amber.json"
    profiles.export_profile(first["id"], export)
    imported = profiles.import_profile(export)
    assert imported["id"] != first["id"]
    assert imported["affection"] == 200
    assert imported["fullness"] == 8
    assert profiles.get(first["id"])["fullness"] == 8
    data = json.loads(export.read_text(encoding="utf-8"))
    assert set(data) == {"format", "version", "profile"}
    assert "pet_mood" not in export.read_text(encoding="utf-8")


def test_invalid_import_and_failed_save_leave_profiles_unchanged(tmp_path):
    settings = {}
    profiles = PetProfiles(settings, lambda: None)
    first = profiles.create("Amber")
    before = json.dumps(settings, sort_keys=True)
    profiles.save = lambda: (_ for _ in ()).throw(OSError("disk failure"))
    with pytest.raises(OSError):
        profiles.update(first["id"], {"mood": 20})
    assert json.dumps(settings, sort_keys=True) == before
    source = tmp_path / "bad.json"
    source.write_text(json.dumps({"format": "frontengine.pet-save", "version": True,
                                  "profile": first}), encoding="utf-8")
    with pytest.raises(ValueError):
        profiles.import_profile(source)
    with pytest.raises(ValueError):
        profiles.update(first["id"], {"id": "0" * 32})
    with pytest.raises(ValueError):
        profiles.update(first["id"], {"fullness": 101})
    with pytest.raises(ValueError):
        profiles.update(first["id"], {"name": "\x00"})
    assert json.dumps(settings, sort_keys=True) == before


def test_profile_capacity_and_atomic_export_failure(tmp_path, monkeypatch):
    profiles = PetProfiles({}, lambda: None)
    first = profiles.create()
    record = profiles.get(first["id"])
    profiles.settings["pet_profiles"]["records"] = {
        f"{index:032x}": {**record, "id": f"{index:032x}"} for index in range(256)}
    with pytest.raises(ValueError, match="256"):
        profiles.create()
    destination = tmp_path / "export.json"
    destination.write_text("existing", encoding="utf-8")
    import frontengine.utils.json.json_file as json_file
    monkeypatch.setattr(json_file.os, "replace", lambda *_args: (_ for _ in ()).throw(OSError("failure")))
    with pytest.raises(OSError):
        profiles.export_profile("0" * 32, destination)
    assert destination.read_text(encoding="utf-8") == "existing"
    assert not Path(str(destination) + ".tmp").exists()


def legacy_profile():
    return {"id": "a" * 32, "name": " Amber ", "mood": 81, "fullness": 32, "affection": 95}


def dressed_profile(profiles):
    record = profiles.create("Amber")
    appearance = record["appearance"]
    appearance["character"] = {"id": "uninstalled.mochi", "version": "1.0"}
    appearance["equipped"]["head"] = {"id": "uninstalled.hat", "version": "2"}
    appearance["saved_outfits"] = [
        {"id": "rainy-day", "name": "Rainy day", "equipped": copy.deepcopy(appearance["equipped"])}]
    return profiles.update(record["id"], {"appearance": appearance, "energy": 42, "mode": "work"})


def test_v1_read_is_lazy_and_failed_migration_restores_original(tmp_path):
    old = legacy_profile()
    settings = {"pet_profiles": {"version": 1, "migrated": True, "records": {old["id"]: old}}}
    before = copy.deepcopy(settings)
    file = JsonRepository(tmp_path / "settings.json")
    file.save(settings)
    profiles = PetProfiles(settings, lambda: (_ for _ in ()).throw(OSError("disk failure")))
    migrated = profiles.get(old["id"])
    assert {key: migrated[key] for key in old} == old
    assert migrated["energy"] == 70 and migrated["mode"] == "play"
    assert migrated["appearance"] == {"character": None, "equipped": dict.fromkeys(
        ("head", "neck", "body", "back")), "saved_outfits": []}
    assert migrated["preferences"] == {"auto_rest": True, "allow_throw": True, "allow_social": True,
                                       "presentation": None}
    assert settings == before
    with pytest.raises(OSError):
        profiles.update(old["id"], {"energy": 12})
    assert settings == before == file.load()
    profiles.save = lambda: file.save(settings)
    profiles.update(old["id"], {"energy": 12})
    assert file.load()["pet_profiles"]["version"] == 2
    assert profiles.get(old["id"])["name"] == old["name"]


def test_outfits_missing_references_clone_export_and_nested_reads_are_independent(tmp_path):
    profiles = PetProfiles({}, lambda: None)
    first = dressed_profile(profiles)
    clone = profiles.create(source=first)
    assert clone["id"] != first["id"]
    assert clone["appearance"] == first["appearance"]
    changed = copy.deepcopy(clone["appearance"])
    changed["equipped"]["head"] = None
    profiles.update(clone["id"], {"appearance": changed})
    assert profiles.get(first["id"])["appearance"] == first["appearance"]
    for detached in (first, clone, profiles.get(first["id"]), profiles.profiles()[0]):
        detached["appearance"]["saved_outfits"][0]["equipped"]["head"]["id"] = "mutated"
        detached["preferences"]["auto_rest"] = False
    saved = profiles.get(first["id"])
    assert saved["appearance"]["saved_outfits"][0]["equipped"]["head"]["id"] == "uninstalled.hat"
    assert saved["preferences"]["auto_rest"] is True
    profiles.update(first["id"], {"mood": 2})
    assert profiles.get(first["id"])["appearance"] == saved["appearance"]
    export = tmp_path / "missing-assets.json"
    profiles.export_profile(first["id"], export)
    assert json.loads(export.read_text(encoding="utf-8"))["version"] == 2
    imported = profiles.import_profile(export)
    assert imported["id"] != first["id"]
    assert imported["appearance"] == saved["appearance"]
    assert imported["mode"] == "work" and imported["energy"] == 42


def test_legacy_import_and_clone_receive_new_identities(tmp_path):
    profiles = PetProfiles({}, lambda: None)
    old = legacy_profile()
    source = tmp_path / "v1.json"
    source.write_text(json.dumps({"format": "frontengine.pet-save", "version": 1, "profile": old}),
                      encoding="utf-8")
    for record in (profiles.import_profile(source), profiles.create(source=old)):
        assert record["id"] != old["id"]
        assert record["name"] == old["name"]
        assert record["affection"] == old["affection"]
        assert record["energy"] == 70


@pytest.mark.parametrize("path,value", [
    (("energy",), True), (("energy",), -1), (("energy",), 101), (("mode",), []),
    (("mode",), "unknown"), (("appearance", "extra"), None),
    (("appearance", "character"), {"id": "hat", "version": True}),
    (("appearance", "character", "id"), "C:\\assets\\mochi"),
    (("appearance", "character", "version"), "../2"),
    (("appearance", "character", "id"), "a" * 129),
    (("appearance", "equipped", "head"), "hat"),
    (("appearance", "equipped", "feet"), None),
    (("appearance", "saved_outfits"), [None]),
    (("appearance", "saved_outfits"), [{"id": "outfit", "name": "Outfit"}]),
    (("preferences", "auto_rest"), 1), (("preferences", "unknown"), True),
])
def test_invalid_v2_nested_values_leave_settings_unchanged(path, value):
    profiles = PetProfiles({}, lambda: None)
    first = dressed_profile(profiles)
    before = copy.deepcopy(profiles.settings)
    invalid = copy.deepcopy(first)
    destination = invalid
    for key in path[:-1]:
        destination = destination[key]
    destination[path[-1]] = value
    with pytest.raises(ValueError):
        profiles.update(first["id"], {path[0]: invalid[path[0]]})
    assert profiles.settings == before


def test_outfit_limit_duplicates_and_schema_versions_are_strict():
    profiles = PetProfiles({}, lambda: None)
    record = dressed_profile(profiles)
    outfit = record["appearance"]["saved_outfits"][0]
    record["appearance"]["saved_outfits"] = [copy.deepcopy(outfit) for _ in range(2)]
    with pytest.raises(ValueError, match="Duplicate"):
        checked_profile(record, 2)
    record["appearance"]["saved_outfits"] = [dict(outfit, id=f"outfit-{i}") for i in range(21)]
    with pytest.raises(ValueError, match="20"):
        checked_profile(record, 2)
    with pytest.raises(ValueError):
        checked_profile(legacy_profile(), 2)
    with pytest.raises(ValueError):
        checked_profile(profiles.get(record["id"]), 1)


def test_save_failure_restores_nested_state_and_absent_store():
    profiles = PetProfiles({}, lambda: None)
    record = dressed_profile(profiles)
    before = copy.deepcopy(profiles.settings)
    profiles.save = lambda: (_ for _ in ()).throw(RuntimeError("failed saver"))
    record["appearance"]["equipped"]["head"] = None
    with pytest.raises(RuntimeError):
        profiles.update(record["id"], {"appearance": record["appearance"]})
    assert profiles.settings == before
    profiles.settings = {}
    with pytest.raises(RuntimeError):
        profiles.create()
    assert profiles.settings == {}
