"""Home saves: validated atomic writes, backups, protection of unreadable files."""
import json
from dataclasses import replace

import pytest

from frontengine.user_setting.pet_game_save import MAX_SAVE_BYTES
from frontengine.utils.pet_game import simulation, snapshot
from frontengine.utils.pet_game.catalog import Catalog, builtin_catalog
from frontengine.utils.pet_game.world import VERSION, World

HOME = "a" * 32
PET = "b" * 32


def _world(mode: str = "manage") -> World:
    world = World(builtin_catalog(), HOME, mode=mode, seed=5)
    zone = world.add_zone("screen", 0, 900, 40)
    world.grant_starter_kit()
    for definition, cell in (("bed_basic", 2), ("table_basic", 7), ("desk_basic", 12)):
        world.place(definition, zone, cell)
    world.add_resident({"id": PET, "name": "Mochi", "mood": 60, "fullness": 70, "affection": 3,
                        "energy": 70}, zone)
    world.create_task("letter", PET, units=3)
    simulation.advance(world, 150000)
    return world


def test_save_and_load_round_trip(tmp_path, *, home_store_factory):
    world = _world()
    store = home_store_factory(tmp_path, builtin_catalog())
    store.save(world)
    store.close()
    result = home_store_factory(tmp_path, builtin_catalog()).load()
    assert result.status == "loaded"
    assert snapshot.to_dict(result.world) == snapshot.to_dict(world)
    assert not (tmp_path / "pet-home.json.tmp").exists()


def test_reload_continues_paused_work_without_paying_again(tmp_path, *, home_store_factory):
    world = _world()
    coins = world.ledger.coins
    store = home_store_factory(tmp_path, builtin_catalog())
    store.save(world)
    loaded = store.load().world
    assert all(task.state == "paused" for task in loaded.tasks.values())
    assert loaded.residents[PET].activity is None
    assert loaded.ledger.coins == coins
    simulation.advance(loaded, 300000)
    assert loaded.ledger.coins > coins


def test_previous_good_save_becomes_the_backup(tmp_path, *, home_store_factory):
    store = home_store_factory(tmp_path, builtin_catalog())
    world = _world()
    store.save(world)
    first = (tmp_path / "pet-home.json").read_bytes()
    simulation.advance(world, 60000)
    store.save(world)
    assert (tmp_path / "pet-home.json.bak").read_bytes() == first


def test_damaged_save_is_never_overwritten_and_backup_can_be_restored(tmp_path, *, home_store_factory):
    store = home_store_factory(tmp_path, builtin_catalog())
    world = _world()
    store.save(world)
    store.save(world)
    store.close()
    (tmp_path / "pet-home.json").write_text("{broken", encoding="utf-8")
    store = home_store_factory(tmp_path, builtin_catalog())
    result = store.load()
    assert result.status == "corrupt"
    assert result.backup_available
    with pytest.raises(PermissionError):
        store.save(world)
    assert (tmp_path / "pet-home.json").read_text(encoding="utf-8") == "{broken"
    restored = store.restore_backup()
    assert restored.status == "loaded"
    store.save(restored.world)
    assert store.load().status == "loaded"
    assert (tmp_path / "pet-home.json.bak").read_bytes() != b"{broken"


def test_newer_version_is_protected(tmp_path, *, home_store_factory):
    store = home_store_factory(tmp_path, builtin_catalog())
    store.save(_world())
    store.close()
    path = tmp_path / "pet-home.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = VERSION + 1
    path.write_text(json.dumps(data), encoding="utf-8")
    original = path.read_bytes()
    store = home_store_factory(tmp_path, builtin_catalog())
    assert store.load().status == "newer"
    another = _world()
    with pytest.raises(PermissionError):
        store.save(another)
    assert path.read_bytes() == original
    kept = store.set_aside("newer1")
    assert kept.read_bytes() == original
    assert not path.exists()
    store.save(_world())
    assert store.load().status == "loaded"


def test_failed_disk_write_keeps_the_old_file_and_memory(tmp_path, *, home_store_factory):
    store = home_store_factory(tmp_path, builtin_catalog())
    world = _world()
    store.save(world)
    before = (tmp_path / "pet-home.json").read_bytes()

    def fail(path, data):
        raise OSError("disk full")

    store.close()
    failing = home_store_factory(tmp_path, builtin_catalog(), write=fail)
    simulation.advance(world, 60000)
    expected = snapshot.to_dict(world)
    with pytest.raises(OSError):
        failing.save(world)
    assert (tmp_path / "pet-home.json").read_bytes() == before
    assert snapshot.to_dict(world) == expected


def test_free_layout_uses_its_own_file(tmp_path, *, home_store_factory):
    managed = home_store_factory(tmp_path, builtin_catalog())
    sandbox = home_store_factory(tmp_path, builtin_catalog(), mode="sandbox")
    managed.save(_world())
    sandbox.save(_world("sandbox"))
    assert managed.path != sandbox.path
    assert managed.load().world.ledger.coins != 0
    managed_world = _world()
    with pytest.raises(ValueError):
        sandbox.save(managed_world)


def test_missing_content_is_kept_and_restored_when_reinstalled(tmp_path, *, home_store_factory):
    full = builtin_catalog()
    world = _world()
    world.ledger.apply("gift", "test", 100)
    world.buy("toy_box", "b1")
    _status, toy = world.place("toy_box", next(iter(world.zones)), 20)
    initial = home_store_factory(tmp_path, full)
    initial.save(world)
    initial.close()
    reduced = Catalog([d for key, d in full.furniture.items() if key != "toy_box"], list(full.recipes.values()), list(full.items.values()))
    store = home_store_factory(tmp_path, reduced)
    partial = store.load().world
    assert toy not in partial.furniture
    assert partial.dormant[0]["record"]["id"] == toy
    store.save(partial)
    store.close()
    restored = home_store_factory(tmp_path, full).load().world
    assert restored.furniture[toy].cell == 20
    assert not restored.dormant


def test_changed_footprints_return_overlapping_pieces_to_storage(tmp_path, *, home_store_factory):
    full = builtin_catalog()
    world = _world()
    initial = home_store_factory(tmp_path, full)
    initial.save(world)
    initial.close()
    wider = replace(full.furniture["bed_basic"], width=8)
    catalog = Catalog([wider if key == "bed_basic" else d for key, d in full.furniture.items()],
                      list(full.recipes.values()), list(full.items.values()))
    loaded = home_store_factory(tmp_path, catalog).load().world
    definitions = sorted(piece.definition for piece in loaded.furniture.values())
    assert definitions == ["bed_basic", "desk_basic"]
    assert loaded.stored("table_basic") == 1


@pytest.mark.parametrize("mutate", [
    lambda data: data.update(format="other"),
    lambda data: data.update(mode="party"),
    lambda data: data["residents"][0].update(zone="z99"),
    lambda data: data["tasks"][0].update(resident="c" * 32),
    lambda data: data["furniture"].append(dict(data["furniture"][0])),
    lambda data: data.update(next_id=2),
    lambda data: data["residents"][0]["needs"].update(energy=101),
    lambda data: data.update(rng=-1),
    lambda data: data.update(extra=1),
])
def test_malformed_saves_are_rejected(tmp_path, mutate, *, home_store_factory):
    data = snapshot.to_dict(_world())
    mutate(data)
    (tmp_path / "pet-home.json").write_text(json.dumps(data), encoding="utf-8")
    assert home_store_factory(tmp_path, builtin_catalog()).load().status == "corrupt"


def test_oversized_save_is_rejected(tmp_path, *, home_store_factory):
    (tmp_path / "pet-home.json").write_bytes(b" " * (MAX_SAVE_BYTES + 1))
    assert home_store_factory(tmp_path, builtin_catalog()).load().status == "corrupt"
