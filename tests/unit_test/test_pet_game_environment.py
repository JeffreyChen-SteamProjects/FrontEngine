"""Atmosphere only: day and night, weather, themes and the life moments they bring."""
import pytest

from frontengine.utils.pet_game import environment, goals, simulation, snapshot
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.schedule import HOUR_MS
from frontengine.utils.pet_game.world import World

HOME = "a" * 32
RESIDENTS = [f"{index:032x}" for index in range(1, 5)]


def _world() -> tuple[World, str]:
    world = World(builtin_catalog(), HOME, seed=2)
    zone = world.add_zone("screen", 0, 900, 48)
    world.grant_starter_kit()
    world.ledger.apply("gift", "test", 2000)
    return world, zone


def _adopt(world: World, zone: str, identifier: str) -> None:
    world.add_resident({"id": identifier, "name": identifier[-1], "mood": 80, "fullness": 90,
                        "affection": 0, "energy": 90}, zone)


def _check(world: World) -> list[str]:
    world.progress.next_check_ms = 0
    goals.update(world)
    return [event["kind"] for event in world.progress.events]


@pytest.mark.parametrize("hour, phase", [(3, "night"), (5, "dawn"), (12, "day"), (17, "dusk"), (22, "night")])
def test_sky_follows_the_game_clock(hour, phase):
    assert environment.sky(hour * HOUR_MS) == phase


def test_daylight_peaks_at_noon_and_is_dark_at_midnight():
    assert environment.daylight(12 * HOUR_MS) == 1.0
    assert environment.daylight(0) == 0.0
    assert 0 < environment.daylight(8 * HOUR_MS) < 1


def test_weather_is_seeded_stable_and_leaves_the_simulation_alone():
    world, _zone = _world()
    state = world.rng.state
    samples = [environment.weather(HOME, hour * HOUR_MS) for hour in range(24 * 10)]
    assert world.rng.state == state
    assert set(samples) <= set(environment.WEATHERS)
    assert len(set(samples)) == 3
    for start in range(0, 24 * 10, environment.WEATHER_SPAN_HOURS):
        assert len(set(samples[start:start + environment.WEATHER_SPAN_HOURS])) == 1
    assert environment.next_change_ms(HOUR_MS) == environment.WEATHER_SPAN_HOURS * HOUR_MS


def test_themes_change_looks_only():
    world, zone = _world()
    world.place("bed_basic", zone, 4)
    before = snapshot.to_dict(world)
    assert world.set_theme(zone, "night_studio") == "accepted"
    assert world.set_theme(zone, "disco") == "unknown"
    after = snapshot.to_dict(world)
    assert after["zones"][0]["theme"] == "night_studio"
    for key in ("furniture", "residents", "ledger", "tasks"):
        assert after[key] == before[key]
    assert snapshot.from_dict(after, builtin_catalog()).zones[zone].theme == "night_studio"


def test_home_milestones_each_happen_once():
    world, zone = _world()
    for identifier in RESIDENTS:
        _adopt(world, zone, identifier)
    for cell in range(30, 40, 2):
        world.buy("plant_pot", f"p{cell}")
        world.place("plant_pot", zone, cell)
    world.progress.stats.update({"settled:story": 1, "settled:herbs": 6, "settled:flowers": 4})
    world.adjust_relation(RESIDENTS[0], RESIDENTS[1], 20)
    world.residents[RESIDENTS[2]].skills["crafting"] = 120
    kinds = _check(world)
    for kind in ("full_house", "green_home", "first_story", "harvest"):
        assert kinds.count(kind) == 1
    assert kinds.count("new_friend") == 2
    assert kinds.count("skilled") == 1
    assert _check(world) == kinds


def test_rain_and_starry_nights_are_noticed_once_a_day():
    world, zone = _world()
    _adopt(world, zone, RESIDENTS[0])
    rain = next(hour for hour in range(24 * 20) if environment.weather(HOME, hour * HOUR_MS) == "rain"
                and environment.sky(hour * HOUR_MS) == "day")
    world.time_ms = rain * HOUR_MS
    assert _check(world).count("rainy_day") == 1
    assert _check(world).count("rainy_day") == 1
    night = next(hour for hour in range(24 * 20) if environment.weather(HOME, hour * HOUR_MS) == "clear"
                 and environment.sky(hour * HOUR_MS) == "night" and hour * HOUR_MS > world.time_ms)
    world.time_ms = night * HOUR_MS
    assert _check(world).count("starry_night") == 1


def test_sleeping_pets_do_not_watch_the_sky():
    world, zone = _world()
    _adopt(world, zone, RESIDENTS[0])
    world.place("bed_basic", zone, 4)
    world.command(RESIDENTS[0], "sleep")
    for _ in range(50):
        simulation.step(world)
    night = next(hour for hour in range(24 * 20) if environment.weather(HOME, hour * HOUR_MS) == "clear"
                 and environment.sky(hour * HOUR_MS) == "night")
    world.time_ms = night * HOUR_MS
    assert world.residents[RESIDENTS[0]].activity.kind == "sleep"
    assert "starry_night" not in _check(world)


def test_reduced_motion_draws_residents_where_the_world_has_them(tmp_path):
    from frontengine.show.pet_game.home_service import HomeService
    from frontengine.show.pet_game.home_strip import HomeStrip
    from frontengine.user_setting.pet_game_save import HomeSaveStore
    from frontengine.user_setting.pet_profiles import PetProfiles

    service = HomeService(None, HomeSaveStore(tmp_path, builtin_catalog()), PetProfiles({}, lambda: None))
    service.create_home("screen", 0, 900, 40, seed=3)
    record = service.profiles.create("Mochi")
    service.adopt(record["id"])
    strip = HomeStrip(service, next(iter(service.world.zones)))
    try:
        resident = service.world.residents[record["id"]]
        strip._before[resident.identifier] = 0
        resident.x_milli = 50_000
        strip.reduced_motion = True
        assert strip.resident_x_milli(resident) == 50_000
        assert strip.button.text().startswith("⌂ ")
    finally:
        strip.close()
        service.shutdown()
