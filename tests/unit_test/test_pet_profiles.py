import json
from pathlib import Path

import pytest

from frontengine.user_setting.pet_profiles import PetProfiles
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
