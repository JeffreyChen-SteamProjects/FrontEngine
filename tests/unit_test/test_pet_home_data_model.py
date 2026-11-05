"""Data-driven event cooldowns, goal windows, furniture art and poses, and moving existing pets in."""
import types

import pytest

from frontengine.show.pet_game.home_service import HomeService
from frontengine.show.pet_game.resident_art import semantic_action
from frontengine.ui.page.pet_game.home_page import PetHomePage
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.user_setting.user_setting_file import user_setting_dict
from frontengine.utils.pet_game import goals
from frontengine.utils.pet_game.catalog import (
    FurnitureDefinition, art_name, builtin_catalog, check_furniture, wanted_poses,
)
from frontengine.utils.pet_game.resident import Activity
from frontengine.utils.pet_game.schedule import DAY_MS
from frontengine.utils.pet_game.world import World

CATALOG = builtin_catalog()


def _world():
    world = World(CATALOG, "a" * 32, seed=2)
    world.add_zone("s", 0, 0, 30)
    return world


def test_event_rules_decide_how_often_an_event_may_happen():
    world = _world()
    pet = "b" * 32
    world.time_ms = 3 * DAY_MS
    assert goals.due(world, "rainy_day")
    goals._life_event(world, "rainy_day", None)
    assert not goals.due(world, "rainy_day")                     # once a day
    world.time_ms += DAY_MS
    assert goals.due(world, "rainy_day")
    goals._life_event(world, "harvest", None)
    world.time_ms += 30 * DAY_MS
    assert not goals.due(world, "harvest")                       # once in a home's life
    goals._life_event(world, "new_friend", pet)
    assert not goals.due(world, "new_friend", pet)
    assert goals.due(world, "new_friend", "c" * 32)              # per pet
    assert set(goals.LIFE_EVENT_RULES) == set(goals.LIFE_EVENTS)


def test_a_goal_outside_its_window_is_hidden_not_failed():
    world = _world()
    spring = goals.Goal("spring_test", lambda w: (1, 1), 5, window=(1, 7))
    winter = goals.Goal("winter_test", lambda w: (1, 1), 5, window=(26, 3))   # wraps over the new year
    world.time_ms = 9 * DAY_MS                                    # day 10 of the year
    assert goals.goal_state(world, spring) == "unavailable"
    assert goals.goal_state(world, winter) == "unavailable"
    world.time_ms = 28 * DAY_MS                                   # day 1 of the next year
    assert goals.goal_state(world, spring) == "done"
    assert goals.goal_state(world, winter) == "done"
    world.progress.goals["spring_test"] = "claimed"
    world.time_ms = 9 * DAY_MS
    assert goals.goal_state(world, spring) == "claimed"           # a claim is never taken back


def test_furniture_names_its_picture_and_the_poses_it_wants():
    bed = CATALOG.furniture["bed_basic"]
    assert art_name(bed) == "bed_basic"
    assert wanted_poses(bed) == ("sleep", "sit")
    custom = FurnitureDefinition("perch", "k", "Perch", "leisure", 1, True, (0,), "relax", art="cat_tree",
                                 poses=("play", "sit"))
    check_furniture(custom)
    assert art_name(custom) == "cat_tree"
    for bad in (dict(art="../escape"), dict(poses=("dance",))):
        with pytest.raises(ValueError):
            check_furniture(FurnitureDefinition("perch", "k", "Perch", "leisure", 1, True, (0,), "relax", **bad))
    with pytest.raises(ValueError):
        check_furniture(FurnitureDefinition("lamp", "k", "Lamp", "decoration", 1, False, poses=("sit",)))


def test_a_character_without_a_pose_uses_the_next_one_the_piece_allows():
    world = _world()
    zone = next(iter(world.zones))
    world.grant_starter_kit()
    world.furnish(zone)
    bed = next(p for p in world.furniture.values() if p.definition == "bed_basic")
    resident = types.SimpleNamespace(activity=Activity("sleep", "tired", bed.identifier, 0, phase="using"))
    sitter = types.SimpleNamespace(has_action=lambda action: action == "sit")
    stander = types.SimpleNamespace(has_action=lambda action: False)
    assert semantic_action(resident, world, sitter) == "sit"
    assert semantic_action(resident, world, stander) == "idle"


@pytest.fixture
def setup(tmp_path, monkeypatch, *, home_store_factory, lifetime_factory):
    lifetime_factory()
    monkeypatch.setitem(user_setting_dict, "pet_home_running", False)
    monkeypatch.setitem(user_setting_dict, "pet_home_on_desktop", False)
    profiles = PetProfiles({}, lambda: None)
    first, second = profiles.create("Mochi"), profiles.create("Pip")
    profiles.update(first["id"], {"mood": 33, "fullness": 44, "affection": 7})
    service = HomeService(None, home_store_factory(tmp_path, CATALOG), profiles)
    page = PetHomePage(service, lifetime=lifetime_factory())
    yield page, profiles, first["id"], second["id"]
    page.shutdown()
    page.deleteLater()


def test_only_the_ticked_pets_move_in_as_themselves(setup):
    page, profiles, first, second = setup
    page.refresh()
    assert page.newcomers.count() == 2
    for index in range(page.newcomers.count()):
        item = page.newcomers.item(index)
        if item.data(0x0100) == second:
            item.setCheckState(page.newcomers.item(index).checkState().Unchecked)
    page.create_home()
    world = page.service.world
    assert set(world.residents) == {first}
    resident = world.residents[first]
    assert (resident.name, resident.needs["mood"], resident.needs["fullness"], resident.affection) == ("Mochi", 33, 44, 7)
    assert len(profiles.profiles()) == 2                          # nothing copied
    assert page.newcomers_box.isHidden()


def test_moving_in_again_later_never_hands_out_the_starter_kit_twice(setup):
    page, _profiles, first, second = setup
    page.refresh()
    page.create_home()
    world = page.service.world
    coins = world.ledger.coins
    assert world.grant_starter_kit() == "duplicate"
    assert page.service.adopt(first) == "duplicate"               # already living here
    assert page.service.release(second) == "accepted"            # moved out, then back in later
    assert page.service.adopt(second) == "accepted"
    assert world.ledger.coins == coins
