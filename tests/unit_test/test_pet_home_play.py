"""Grooming, toys, calling a pet over, tag between two pets, and a pet's own photo."""
from pathlib import Path

import pytest

from frontengine.show.pet_game.home_service import HomeService
from frontengine.ui.page.pet_game.home_page import PetHomePage
from frontengine.user_setting.pet_game_save import HomeSaveStore
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.user_setting.user_setting_file import user_setting_dict
from frontengine.utils.pet_game import behaviour, simulation
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.world import World

CATALOG = builtin_catalog()
A, B = "b" * 32, "c" * 32


def _world():
    world = World(CATALOG, "a" * 32, seed=8)
    zone = world.add_zone("s", 0, 0, 40)
    for identifier, x in ((A, 300), (B, 500)):
        world.add_resident({"id": identifier, "name": identifier[:4], "mood": 50, "fullness": 80,
                            "affection": 1, "energy": 80}, zone)
        world.residents[identifier].x_milli = x * 1000
    return world


def test_grooming_lifts_comfort_and_a_toy_waits_until_work_is_done():
    world = _world()
    pet = world.residents[A]
    comfort = pet.needs["comfort"]
    assert world.interact(A, "groom") == "accepted"
    assert pet.needs["comfort"] == comfort + 12
    behaviour.start(world, pet, "work", "command")
    assert world.interact(A, "toy") == "busy"
    assert world.interact(A, "pat") == "accepted"                # gentle care is fine at any time


def test_calling_a_pet_walks_it_over_unless_it_is_eating():
    world = _world()
    pet = world.residents[A]
    assert world.call(A, 900_000) == "accepted"
    assert (pet.activity.kind, pet.activity.target_x) == ("come", 900_000)
    for _ in range(200):
        simulation.step(world)
        if pet.x_milli == 900_000:
            break
    for _ in range(30):                                        # it stays a while where it was called
        simulation.step(world)
    assert pet.x_milli == 900_000
    assert pet.activity.kind == "come"
    behaviour.start(world, pet, "eat", "hungry")
    assert world.call(A, 0) == "busy"
    assert pet.activity.kind == "eat"


def test_tag_needs_a_free_partner_and_cheers_both_up():
    world = _world()
    world.park(B, True)
    assert world.play_tag(A) == "no_partner"
    world.park(B, False)
    assert world.play_tag(A) == "accepted"
    chaser, runner = world.residents[A], world.residents[B]
    assert chaser.activity.kind == runner.activity.kind == "tag"
    assert chaser.activity.partner == B
    moods = chaser.needs["mood"], runner.needs["mood"]
    for _ in range(80):
        simulation.step(world)
    assert chaser.needs["mood"] > moods[0]
    assert runner.needs["mood"] > moods[1]
    assert world.relation(A, B) > 0


def test_a_busy_pet_is_never_dragged_into_tag():
    world = _world()
    behaviour.start(world, world.residents[B], "work", "command")
    assert world.play_tag(A) == "no_partner"
    assert world.residents[B].activity.kind == "work"


@pytest.fixture
def page(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setitem(user_setting_dict, "pet_home_running", False)
    monkeypatch.setitem(user_setting_dict, "pet_home_on_desktop", True)
    service = HomeService(None, HomeSaveStore(tmp_path, CATALOG), PetProfiles({}, lambda: None))
    widget = PetHomePage(service)
    widget.resize(1200, 900)
    widget.show()
    widget.create_home()
    widget.residents.new_pet()
    yield widget
    widget.shutdown()
    widget.close()
    widget.deleteLater()


def test_a_pet_photo_lands_in_the_album(page):
    resident = next(iter(page.service.world.residents.values()))
    page.strip_list[0].action_requested.emit("photo", resident.identifier)
    photos = list((Path.cwd() / "pet-album").glob("*.png"))
    assert len(photos) == 1
    assert photos[0].stem.endswith(resident.name.replace(" ", ""))
