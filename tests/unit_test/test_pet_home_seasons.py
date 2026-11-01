"""Seasons in the home's year, seasonal goals that are never missed for good, and advanced trades."""
from frontengine.ui.page.pet_game.home_things import thing_icon
from frontengine.utils.pet_game import goals
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.environment import SEASONS, season, weather
from frontengine.utils.pet_game.schedule import DAY_MS, HOUR_MS
from frontengine.utils.pet_game.world import World

CATALOG = builtin_catalog()
HOME = "a" * 32
PET = "b" * 32


def test_the_year_turns_every_four_weeks():
    assert [season(day * DAY_MS) for day in (0, 7, 14, 21, 28)] == [*SEASONS, "spring"]


def test_winter_rain_falls_as_snow_and_other_seasons_never_snow():
    winter = [weather(HOME, (21 + day) * DAY_MS + hour * HOUR_MS) for day in range(7) for hour in range(0, 24, 6)]
    others = [weather(HOME, day * DAY_MS + hour * HOUR_MS) for day in range(21) for hour in range(0, 24, 6)]
    assert "snow" in winter
    assert "rain" not in winter
    assert "snow" not in others


def _world():
    world = World(CATALOG, HOME, seed=3)
    zone = world.add_zone("s", 0, 0, 40)
    world.grant_starter_kit()
    world.furnish(zone)
    return world, zone


def test_a_seasonal_goal_is_offered_in_its_season_and_paid_once():
    world, _zone = _world()
    spring = next(goal for goal in goals.SEASONAL if goal.identifier == "spring_flowers")
    world.progress.stats["settled:flowers"] = 2
    world.time_ms = 8 * DAY_MS                                   # summer
    assert goals.goal_state(world, spring) == "unavailable"
    assert goals.claim(world, "spring_flowers") == "not_ready"
    world.time_ms = 28 * DAY_MS                                  # spring again, a year on
    coins = world.ledger.coins
    assert goals.claim(world, "spring_flowers") == "accepted"
    assert world.ledger.coins == coins + spring.coins
    assert goals.claim(world, "spring_flowers") == "not_ready"   # once only
    assert {goal.window for goal in goals.SEASONAL} == {(1, 7), (8, 14), (15, 21), (22, 28)}


def test_advanced_trades_need_a_skilled_pet_in_a_grown_home(monkeypatch):
    world, zone = _world()
    world.ledger.apply("gift", "test", 2000, {"flower": 6})
    world.buy_and_place("planter", zone, "p1")
    world.add_resident({"id": PET, "name": "Pip", "mood": 80, "fullness": 80, "affection": 1, "energy": 90}, zone)
    pet = world.residents[PET]
    pet.skills["gardening"] = 0
    assert world.create_task("bouquet", PET)[0] == "skill_too_low"
    pet.skills["gardening"] = 2000                               # skilled: level 4 and more
    assert world.create_task("bouquet", PET)[0] == "locked"       # a young home does not offer it yet
    monkeypatch.setattr(goals, "home_level", lambda w: 4)
    assert world.create_task("bouquet", PET)[0] == "accepted"
    for name in ("novel", "bouquet", "music_box"):
        assert (CATALOG.recipes[name].min_level, CATALOG.recipes[name].unlock_level) == (4, 4)
        assert not thing_icon("recipe:" + name).isNull()
    for item in ("bouquet", "music_box"):
        assert not thing_icon(item).isNull()
