"""Residents together: comfort and company, greetings, shared meals, small quarrels, personality."""
import pytest

from frontengine.utils.pet_game import simulation, snapshot
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.resident import TRAITS, traits_for
from frontengine.utils.pet_game.world import World

HOME = "a" * 32
A, B = "b" * 32, "c" * 32
MINUTE = 60000


def _home() -> tuple[World, str]:
    world = World(builtin_catalog(), HOME, seed=9)
    zone = world.add_zone("screen", 0, 900, 48)
    world.grant_starter_kit()
    world.ledger.apply("gift", "test", 1000)
    for definition, cell in (("bed_basic", 2), ("table_basic", 7), ("desk_basic", 12)):
        world.place(definition, zone, cell)
    for identifier, name in ((A, "Mochi"), (B, "Pip")):
        world.add_resident({"id": identifier, "name": name, "mood": 80, "fullness": 90, "affection": 0,
                            "energy": 90}, zone)
        world.residents[identifier].traits = ()
    return world, zone


def _run(world: World, minutes: float) -> list[dict]:
    events = []
    for _ in range(int(minutes * MINUTE) // simulation.STEP_MS):
        simulation.step(world)
        events += world.drain_events()
    return events


def test_version_one_homes_gain_comfort_and_company_on_load():
    world, _zone = _home()
    data = snapshot.to_dict(world)
    data["version"] = 1
    del data["relations"]
    for resident in data["residents"]:
        resident["needs"] = {key: resident["needs"][key] for key in ("energy", "fullness", "mood")}
    loaded = snapshot.from_dict(data, builtin_catalog())
    assert loaded.residents[A].needs["comfort"] == 60
    assert loaded.residents[A].needs["social"] == 60
    assert loaded.relations == {}
    assert snapshot.to_dict(loaded)["version"] == 2


def test_relationships_survive_saving_and_reject_bad_pairs():
    world, _zone = _home()
    world.adjust_relation(A, B, 7)
    data = snapshot.to_dict(world)
    assert snapshot.from_dict(data, builtin_catalog()).relation(B, A) == 7
    data["relations"] = {f"{B}|{A}": 3}
    catalog = builtin_catalog()
    with pytest.raises(ValueError):
        snapshot.from_dict(data, catalog)


def test_lonely_residents_greet_and_become_friends():
    world, _zone = _home()
    for identifier in (A, B):
        world.residents[identifier].needs["social"] = 20
    world.residents[B].x_milli = world.residents[A].x_milli + 100_000
    events = _run(world, 0.5)
    assert any(event["kind"] == "greeted" for event in events)
    assert world.relation(A, B) == 2
    assert world.residents[A].needs["social"] > 20
    assert world.residents[B].needs["social"] > 20


def test_eating_together_is_better_company_and_brings_them_closer():
    def company(shared: bool) -> int:
        world, _zone = _home()
        for identifier in (A, B):
            world.residents[identifier].needs.update(fullness=30, social=30)
        world.command(A, "eat")
        if shared:
            world.command(B, "eat")
        else:
            world.park(B, True)
        _run(world, 0.75)
        return world.residents[A].needs["social"]
    assert company(True) > company(False) + 5
    world, _zone = _home()
    for identifier in (A, B):
        world.residents[identifier].needs.update(fullness=60)
        world.command(identifier, "eat")
    events = _run(world, 1.5)
    assert any(event["kind"] == "shared" for event in events)
    assert world.relation(A, B) >= 1


def test_wanting_the_same_seat_starts_a_small_quarrel_once():
    world, zone = _home()
    world.buy("armchair", "chair")
    world.place("armchair", zone, 20)
    world.command(A, "relax")
    _run(world, 0.4)
    assert world.residents[A].activity.kind == "relax"
    mood = world.residents[B].needs["mood"]
    world.command(B, "relax")
    _run(world, 0.1)
    assert world.relation(A, B) == -1
    assert world.residents[B].needs["mood"] <= mood - 2
    world.command(B, "relax")
    _run(world, 0.1)
    assert world.relation(A, B) == -1           # cooled down, not repeated


def test_leaving_the_home_forgets_relationships():
    world, _zone = _home()
    world.adjust_relation(A, B, 5)
    world.remove_resident(B)
    assert world.relations == {}


def test_discomfort_wears_on_mood():
    def mood_after(comfort: int) -> int:
        world, _zone = _home()
        world.park(B, True)
        resident = world.residents[A]
        resident.needs.update(comfort=comfort, mood=70)
        resident.decide_after_ms = 10 ** 12          # stand still so only base rates apply
        _run(world, 5)
        return resident.needs["mood"]
    assert mood_after(10) < mood_after(90)


def test_personality_is_stable_varied_and_speeds_liked_work():
    first, again = traits_for(A), traits_for(A)
    assert first == again
    assert len(set(traits_for(A))) == 2
    seen = {trait for index in range(40) for trait in traits_for(f"{index:032x}")}
    assert seen == set(TRAITS)

    def progress(traits) -> int:
        world, zone = _home()
        world.park(B, True)
        world.residents[A].traits = traits
        world.buy("planter", "planter")
        world.place("planter", zone, 18)
        _status, task = world.create_task("herbs", A)
        _run(world, 1)
        return world.tasks[task].progress_ms
    assert progress(("green_thumb",)) > progress(())


def test_the_card_names_personality_friends_and_time_left():
    from frontengine.show.pet_game.captions import card_text
    world, _zone = _home()
    world.residents[A].traits = ("green_thumb", "quiet")
    world.adjust_relation(A, B, 9)
    world.create_task("letter", A)
    _run(world, 0.2)
    text = card_text(world.residents[A], world)
    assert "Pip (+9)" in text
    assert "loves gardening" in text
    assert "min left" in text


def test_desktop_bubbles_follow_events(tmp_path):
    from frontengine.show.pet_game.home_service import HomeService
    from frontengine.show.pet_game.home_strip import HomeStrip, bubble_text
    from frontengine.user_setting.pet_game_save import HomeSaveStore
    from frontengine.user_setting.pet_profiles import PetProfiles

    assert bubble_text({"kind": "greeted"}) == "Hi!"
    assert bubble_text({"kind": "settled", "coins": 12}) == "+12"
    assert bubble_text({"kind": "activity", "activity": "wander"}) == ""
    service = HomeService(None, HomeSaveStore(tmp_path, builtin_catalog()), PetProfiles({}, lambda: None))
    service.create_home("screen", 0, 900, 40, seed=3)
    record = service.profiles.create("Mochi")
    service.adopt(record["id"])
    strip = HomeStrip(service, next(iter(service.world.zones)))
    try:
        strip._events([{"kind": "greeted", "resident": record["id"]}])
        strip.update_mask()
        resident = service.world.residents[record["id"]]
        bubble = strip.bubble_rect(resident)
        assert bubble is not None
        assert strip.mask().contains(bubble.center().toPoint())
    finally:
        strip.close()
        service.shutdown()
