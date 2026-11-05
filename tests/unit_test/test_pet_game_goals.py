"""Growth without pressure: goals pay once, commissions are seeded, wishes and events come from living."""
import pytest

from frontengine.utils.pet_game import goals, simulation, snapshot
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.schedule import DAY_MS
from frontengine.utils.pet_game.world import World

HOME = "a" * 32
A, B, C = "b" * 32, "c" * 32, "d" * 32
MINUTE = 60000


def _world(coins: int = 1000) -> tuple[World, str]:
    world = World(builtin_catalog(), HOME, seed=5)
    zone = world.add_zone("screen", 0, 900, 48)
    world.grant_starter_kit()
    world.ledger.apply("gift", "test", coins)
    return world, zone


def _adopt(world: World, zone: str, identifier: str, name: str = "Pet") -> None:
    world.add_resident({"id": identifier, "name": name, "mood": 80, "fullness": 90, "affection": 0,
                        "energy": 90}, zone)
    world.residents[identifier].traits = ()


def _run(world: World, minutes: float) -> list[dict]:
    events = []
    for _ in range(int(minutes * MINUTE) // simulation.STEP_MS):
        simulation.step(world)
        events += world.drain_events()
    return events


def _states(world: World) -> dict[str, str]:
    return {goal.identifier: goals.goal_state(world, goal) for goal in goals.TUTORIAL}


def test_tutorial_goals_follow_play_and_pay_once():
    world, zone = _world()
    assert set(_states(world).values()) == {"open"}
    _adopt(world, zone, A)
    world.place("bed_basic", zone, 2)
    assert _states(world)["move_in"] == "done"
    assert _states(world)["place_bed"] == "done"
    coins = world.ledger.coins
    assert goals.claim(world, "move_in") == "accepted"
    assert world.ledger.coins == coins + 5
    assert goals.claim(world, "move_in") == "not_ready"
    assert goals.claim(world, "second_resident") == "not_ready"
    assert world.ledger.coins == coins + 5


def test_skipping_the_tutorial_pays_nothing_and_keeps_it_reviewable():
    world, zone = _world()
    coins = world.ledger.coins
    goals.skip_tutorial(world)
    assert set(_states(world).values()) == {"skipped"}
    assert world.ledger.coins == coins
    _adopt(world, zone, A)
    assert goals.claim(world, "move_in") == "not_ready"


def test_life_milestones_raise_the_home_level():
    world, zone = _world()
    assert goals.home_level(world) == 1
    for identifier in (A, B, C):
        _adopt(world, zone, identifier)
    assert goals.home_level(world) == 2


def test_commissions_are_seeded_by_day_and_leave_the_simulation_alone():
    world, _zone = _world()
    state = world.rng.state
    goals.refresh_commissions(world)
    first = [dict(offer) for offer in world.progress.commissions["offers"]]
    assert world.rng.state == state
    assert len(first) == 3
    again, _zone = _world()
    goals.refresh_commissions(again)
    assert again.progress.commissions["offers"] == first
    world.time_ms += DAY_MS
    goals.refresh_commissions(world)
    assert world.progress.commissions["day"] == 2


def test_commissions_notify_once_when_the_day_changes():
    world, _zone = _world()
    world.drain_events()
    goals.refresh_commissions(world)
    assert world.drain_events() == [{"kind": "commissions_refreshed", "time": world.time_ms, "day": 1}]
    goals.refresh_commissions(world)
    assert world.drain_events() == []
    world.time_ms += DAY_MS
    goals.refresh_commissions(world)
    assert world.drain_events() == [{"kind": "commissions_refreshed", "time": world.time_ms, "day": 2}]


def test_delivering_a_commission_pays_once_and_needs_the_goods():
    world, _zone = _world()
    goals.refresh_commissions(world)
    offer = world.progress.commissions["offers"][0]
    assert goals.deliver(world, 0) == "none_stored"
    world.ledger.apply("stock", "test", 0, {offer["item"]: offer["count"]})
    coins = world.ledger.coins
    assert goals.deliver(world, 0) == "accepted"
    assert world.ledger.coins == coins + offer["coins"]
    assert world.ledger.count(offer["item"]) == 0
    assert goals.deliver(world, 0) == "unknown"


def test_a_granted_wish_lifts_mood_and_rests_before_the_next():
    world, zone = _world()
    _adopt(world, zone, A)
    _run(world, 0.6)
    state = world.progress.wishes[A]
    assert state["wish"] in goals.WISHES
    state.update(wish="plant", base=goals.placed(world, "decoration"))
    resident = world.residents[A]
    resident.needs["mood"] = 50
    world.buy("plant_pot", "plant")
    world.place("plant_pot", zone, 30)
    events = _run(world, 0.6)
    assert any(event["kind"] == "wish_granted" for event in events)
    assert world.progress.wishes[A]["wish"] is None
    assert resident.affection == 3


def test_life_events_come_from_living():
    world, zone = _world()
    _adopt(world, zone, A)
    world.progress.stats["settled:toy"] = 1
    world.progress.arrivals[A] = world.time_ms - 7 * DAY_MS
    _run(world, 0.6)
    kinds = [event["kind"] for event in world.progress.events]
    assert kinds.count("first_creation") == 1
    assert kinds.count("birthday") == 1
    _run(world, 0.6)
    assert [event["kind"] for event in world.progress.events] == kinds


def test_the_celebration_needs_company_and_all_three_jobs_and_happens_once():
    world, zone = _world()
    _adopt(world, zone, A)
    _adopt(world, zone, B)
    assert goals.celebrate(world) == "not_ready"
    for recipe in ("letter", "herbs", "toy"):
        world.progress.stats["settled:" + recipe] = 1
    coins = world.ledger.coins
    assert goals.celebrate(world) == "accepted"
    assert world.ledger.coins == coins + goals.CELEBRATION_COINS
    assert goals.celebrate(world) == "not_ready"
    assert world.progress.events[-1]["kind"] == "celebration"


def test_progress_survives_saving_and_older_homes_start_counting():
    world, zone = _world()
    _adopt(world, zone, A)
    _run(world, 1)
    goals.claim(world, "move_in")
    data = snapshot.to_dict(world)
    loaded = snapshot.from_dict(data, builtin_catalog())
    assert loaded.progress.to_dict() == world.progress.to_dict()
    data["version"] = 2
    del data["progress"]
    older = snapshot.from_dict(data, builtin_catalog())
    assert older.progress.arrivals == {A: older.time_ms}
    assert older.progress.goals == {}


@pytest.mark.parametrize("change", [
    {"goals": {"move_in": "paid"}}, {"commissions": {"day": 1, "offers": [{"item": "gold", "count": 1,
                                                                             "coins": 9, "done": False}]}},
    {"events": [{"kind": "party", "day": 1, "resident": None}]}, {"stats": {"x": -1}},
])
def test_malformed_progress_is_rejected(change):
    world, _zone = _world()
    data = snapshot.to_dict(world)
    data["progress"].update(change)
    catalog = builtin_catalog()
    with pytest.raises(ValueError):
        snapshot.from_dict(data, catalog)


def test_the_goals_panel_claims_and_saves_a_game_only_photo(tmp_path, monkeypatch, *, home_store_factory, lifetime_factory):
    from PySide6.QtGui import QImage
    from frontengine.show.pet_game.home_service import HomeService
    from frontengine.ui.page.pet_game.home_page import PetHomePage
    from frontengine.user_setting.pet_profiles import PetProfiles
    from frontengine.user_setting.user_setting_file import user_setting_dict

    monkeypatch.chdir(tmp_path)
    lifetime_factory()
    monkeypatch.setitem(user_setting_dict, "pet_home_on_desktop", False)
    monkeypatch.setitem(user_setting_dict, "pet_home_running", False)
    service = HomeService(None, home_store_factory(tmp_path, builtin_catalog()), PetProfiles({}, lambda: None))
    page = PetHomePage(service, lifetime=lifetime_factory())
    try:
        page.create_home()
        # creating a home with no pets brings a first one
        page.refresh()
        panel = page.goals
        assert panel.level.text() == "Home level 1"
        panel.tutorial.setCurrentRow(0)
        coins = service.world.ledger.coins
        panel.claim()
        assert service.world.ledger.coins == coins + 5
        photo = panel.take_photo()
        assert photo.parent.name == "pet-album"
        assert not QImage(str(photo)).isNull()
    finally:
        page.shutdown()
