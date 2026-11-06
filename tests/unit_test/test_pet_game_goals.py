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


@pytest.mark.parametrize('groups', [(0, 1, 2), (0, 0, 1), (0, 0, 0)])
@pytest.mark.parametrize('mode', ['manage', 'sandbox'])
def test_friends_dinner_requires_three_diners_in_one_zone(groups, mode):
    world = World(builtin_catalog(), HOME, mode=mode, seed=9)
    if mode == 'manage':
        world.ledger.apply('test-capital', 'test', 1000)
    zones = {group: world.add_zone(f'screen-{group}', group * 1000, 900, 48)
             for group in sorted(set(groups))}
    for number, group in enumerate(groups):
        assert world.buy('round_table', f'table-{number}') == 'accepted'
        assert world.place('round_table', zones[group], 7 + number * 6)[0] == 'accepted'
        identifier = f'{number + 1:032x}'
        _adopt(world, zones[group], identifier)
        world.residents[identifier].needs['fullness'] = 30
        assert world.command(identifier, 'eat') == 'accepted'
    events = _run(world, 1)
    dinners = [event for event in events if event.get('event') == 'friends_dinner']
    assert len(dinners) == (1 if len(zones) == 1 else 0)
    loaded = snapshot.from_dict(snapshot.to_dict(world), world.catalog)
    assert loaded.progress.event_days == world.progress.event_days


@pytest.mark.parametrize('together', [False, True])
@pytest.mark.parametrize('mode', ['manage', 'sandbox'])
def test_dinner_service_inbox_and_saved_marker(tmp_path, monkeypatch, home_store_factory,
                                               lifetime_factory, together, mode):
    from pathlib import Path
    import subprocess
    import sys

    from frontengine.show.pet_game.home_service import HomeService
    from frontengine.ui.page.pet_game.home_page import PetHomePage
    from frontengine.user_setting.user_setting_file import user_setting_dict

    lifetime = lifetime_factory()
    monkeypatch.setitem(user_setting_dict, 'pet_home_on_desktop', False)
    monkeypatch.setitem(user_setting_dict, 'pet_home_running', False)
    store = home_store_factory(tmp_path, builtin_catalog(), mode)
    service = HomeService(None, store, store.storage.profiles())
    page = PetHomePage(service, lifetime=lifetime)
    try:
        world = service.create_home('screen', 0, 900, 48, seed=9)
        service.pause('audit')
        world.automatic = False
        first_zone = next(iter(world.zones))
        if mode == 'manage':
            world.ledger.apply('test-capital', 'test', 1000)
        for number in range(3):
            zone = first_zone if together or number == 0 else world.add_zone(
                f'screen-{number}', number * 1000, 900, 48)
            assert world.buy('round_table', f'table-{number}') == 'accepted'
            assert world.place('round_table', zone, 7 + number * 6)[0] == 'accepted'
            record = service.profiles.create(f'Pet {number}')
            assert service.adopt(record['id'], zone) == 'accepted'
            resident = world.residents[record['id']]
            resident.traits = ()
            resident.needs.update(fullness=30, energy=90)
            assert world.command(record['id'], 'eat') == 'accepted'
        for _ in range(300):
            simulation.step(world)
            service._publish()
        dinners = [entry for entry in page.inbox.entries
                   if entry['event'].get('event') == 'friends_dinner']
        assert len(dinners) == int(together)
        if together:
            assert dinners[0]['count'] == 1
            assert 'Dinner with friends' in [page.inbox.list.item(i).text()
                                           for i in range(page.inbox.list.count())]
        service._publish()
        assert service.save_now()
        loaded = store.load()
        assert loaded.status == 'loaded'
        assert loaded.world.progress.event_days == world.progress.event_days
        assert bool(loaded.world.progress.event_days.get('friends_dinner')) == together
        assert len([entry for entry in page.inbox.entries
                    if entry['event'].get('event') == 'friends_dinner']) == int(together)
        child = subprocess.run([sys.executable, '-c', '''
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from frontengine.utils.pet_game import simulation, snapshot
from frontengine.utils.pet_game.catalog import builtin_catalog
data = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
world = snapshot.from_dict(data, builtin_catalog())
assert snapshot.to_dict(world) == data
assert not world.drain_events()
markers = dict(world.progress.event_days.get('friends_dinner', {}))
assert bool(markers) == (sys.argv[3] == 'True')
for resident in world.residents.values():
    resident.needs.update(fullness=30, energy=90)
    assert world.command(resident.identifier, 'eat') == 'accepted'
events = []
for _ in range(300):
    simulation.step(world)
    events.extend(world.drain_events())
assert not any(event.get('event') == 'friends_dinner' for event in events)
assert world.progress.event_days.get('friends_dinner', {}) == markers
print('cold dinner markers preserved; no duplicate event')
''', str(Path(__file__).resolve().parents[2]), str(store.path), str(together)],
                               capture_output=True, text=True, timeout=60)
        assert child.returncode == 0, child.stdout + child.stderr
    finally:
        page.shutdown()


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


@pytest.mark.parametrize("arrival_offset", [0, DAY_MS // 2, DAY_MS - goals.CHECK_MS])
@pytest.mark.parametrize("reload", [False, True])
def test_birthday_is_once_per_arrival_anniversary_across_calendar_days(arrival_offset, reload):
    world, zone = _world()
    world.automatic = False
    world.time_ms = arrival_offset
    _adopt(world, zone, A)
    world.residents[A].needs["mood"] = 20
    world.progress.wishes[A] = {"wish": "play_time", "base": 0, "ready": 0}
    events = []
    for cycle in (1, 2):
        start = arrival_offset + cycle * goals.BIRTHDAY_EVERY_DAYS * DAY_MS
        for time in (start, start + DAY_MS - goals.CHECK_MS):
            world.time_ms = time
            goals.update(world)
            events.extend(event for event in world.drain_events()
                          if event["kind"] == "life_event" and event["event"] == "birthday")
            if reload:
                world = snapshot.from_dict(snapshot.to_dict(world), world.catalog)
                world.automatic = False
        assert len(events) == cycle
        assert world.residents[A].needs["mood"] == 20 + cycle * 10


@pytest.mark.parametrize("version", [7, 8])
@pytest.mark.parametrize("recorded_day", [8, 9])
def test_saved_birthday_marker_blocks_same_anniversary_but_not_next(version, recorded_day):
    world, zone = _world()
    world.time_ms = DAY_MS // 2
    _adopt(world, zone, A)
    world.residents[A].needs["mood"] = 20
    world.progress.wishes[A] = {"wish": "play_time", "base": 0, "ready": 0}
    world.progress.events = [{"kind": "birthday", "day": recorded_day, "resident": A}]
    world.progress.event_days = {"birthday": {A: recorded_day}}
    data = snapshot.to_dict(world)
    data["version"] = version
    if version == 7:
        del data["progress"]["event_days"]
    world = snapshot.from_dict(data, world.catalog)
    world.automatic = False
    world.time_ms = 8 * DAY_MS
    goals.update(world)
    assert not [e for e in world.drain_events() if e.get("event") == "birthday"]
    assert world.residents[A].needs["mood"] == 20
    world.time_ms = 14 * DAY_MS + DAY_MS // 2
    goals.update(world)
    assert len([e for e in world.drain_events() if e.get("event") == "birthday"]) == 1
    assert world.residents[A].needs["mood"] == 30
