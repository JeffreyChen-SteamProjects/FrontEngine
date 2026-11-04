import pytest

from frontengine.utils.pet_game import goals, snapshot
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.schedule import DAY_MS
from frontengine.utils.pet_game.world import World


def _world():
    world = World(builtin_catalog(), "a" * 32, seed=3)
    world.add_zone("screen", 0, 0, 30)
    return world


@pytest.mark.parametrize("kind", goals.LIFE_EVENTS)
def test_event_frequency_survives_history_rollover_and_save(kind):
    world = _world()
    resident = "b" * 32 if goals.LIFE_EVENT_RULES[kind].per_resident else None
    goals._life_event(world, kind, resident)
    for _ in range(goals.MAX_EVENTS):
        goals._life_event(world, "starry_night" if kind != "starry_night" else "rainy_day", None)
    assert not any(event["kind"] == kind for event in world.progress.events)
    assert not goals.due(world, kind, resident)
    loaded = snapshot.from_dict(snapshot.to_dict(world), world.catalog)
    assert not goals.due(loaded, kind, resident)
    loaded.time_ms += DAY_MS
    assert goals.due(loaded, kind, resident) == bool(goals.LIFE_EVENT_RULES[kind].cooldown_days)
    if resident:
        assert goals.due(loaded, kind, "c" * 32)


def test_legacy_history_migrates_latest_day_without_emitting():
    world = _world()
    data = snapshot.to_dict(world)
    data["version"] = 7
    data["progress"].pop("event_days", None)
    data["progress"]["events"] = [
        {"kind": "rainy_day", "day": day, "resident": None} for day in (4, 2)]
    loaded = snapshot.from_dict(data, world.catalog)
    assert loaded.drain_events() == []
    for day in (2, 4):
        loaded.time_ms = (day - 1) * DAY_MS
        assert not goals.due(loaded, "rainy_day")
    loaded.time_ms = 4 * DAY_MS
    assert goals.due(loaded, "rainy_day")


def test_departed_residents_keep_lifetime_events_beyond_64_identities():
    world = _world()
    zone = next(iter(world.zones))
    for number in range(70):
        identifier = f"{number:032x}"
        world.add_resident({"id": identifier, "name": "Pet", "mood": 80, "fullness": 80,
                            "affection": 0, "energy": 80}, zone)
        goals._life_event(world, "skilled", identifier)
        world.remove_resident(identifier)
    loaded = snapshot.from_dict(snapshot.to_dict(world), world.catalog)
    identifier = "0" * 32
    loaded.add_resident({"id": identifier, "name": "Pet", "mood": 80, "fullness": 80,
                        "affection": 0, "energy": 80}, zone)
    assert not goals.due(loaded, "skilled", identifier)


@pytest.mark.parametrize("value", [None, [], {"unknown": {}}, {"rainy_day": {"b" * 32: 1}},
                                   {"skilled": {"": 1}}, {"skilled": {"bad": 1}},
                                   *({"rainy_day": {"": day}} for day in (True, 0, -1, 10 ** 7 + 1))])
def test_malformed_event_days_are_rejected(value):
    world = _world()
    data = snapshot.to_dict(world)
    data["progress"]["event_days"] = value
    with pytest.raises(ValueError):
        snapshot.from_dict(data, world.catalog)


def test_current_save_requires_persistent_event_days():
    data = snapshot.to_dict(_world())
    data["progress"].pop("event_days", None)
    with pytest.raises(ValueError):
        snapshot.from_dict(data, builtin_catalog())


def test_repeated_daily_events_update_one_marker_and_clock_rollback_stays_blocked():
    world = _world()
    for day in range(60):
        world.time_ms = day * DAY_MS
        goals._life_event(world, "rainy_day", None)
    loaded = snapshot.from_dict(snapshot.to_dict(world), world.catalog)
    assert loaded.progress.event_days == {"rainy_day": {"": 60}}
    loaded.time_ms = DAY_MS
    assert not goals.due(loaded, "rainy_day")


@pytest.mark.parametrize("resident", [None, "bad"])
def test_legacy_resident_event_cannot_migrate_an_invalid_scope(resident):
    data = snapshot.to_dict(_world())
    data["version"] = 7
    del data["progress"]["event_days"]
    data["progress"]["events"] = [{"kind": "skilled", "day": 1, "resident": resident}]
    with pytest.raises(ValueError):
        snapshot.from_dict(data, builtin_catalog())
