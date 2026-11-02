"""The second furniture collection: ten more pieces, each drawn for every theme, used by the pets for
what it is for, and opening with the home level."""
import pytest

from frontengine.show.pet_game.furniture_art import picture
from frontengine.utils.pet_game import behaviour
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.layout import THEMES
from frontengine.utils.pet_game.world import World

CATALOG = builtin_catalog()
NEW = ("floor_lamp", "hanging_plants", "wardrobe_closet", "futon", "kotatsu", "tv_set", "fireplace",
       "rocking_horse", "telescope", "shower")
PET = "b" * 32


def test_the_collection_has_forty_five_pieces_and_every_new_one_is_drawn():
    assert len(CATALOG.furniture) == 45
    for name in NEW:
        definition = CATALOG.furniture[name]
        assert 1 <= definition.unlock_level <= 5
        assert 0 < definition.sell_back <= definition.price // 2 + 1
        for theme in THEMES:
            image = picture(theme, name)
            assert image is not None and not image.isNull(), (theme, name)


def _home():
    world = World(CATALOG, "a" * 32, "sandbox", seed=4)
    zone = world.add_zone("s", 0, 0, 40)
    world.add_resident({"id": PET, "name": "Mochi", "mood": 60, "fullness": 90, "affection": 1, "energy": 90}, zone)
    return world, zone, world.residents[PET]


def _only(world, zone, name, cell=20):
    world.buy(name, f"buy-{name}")
    assert world.place(name, zone, cell)[0] == "accepted"


@pytest.mark.parametrize("name, need, value, activity", [
    ("shower", "hygiene", 10, "wash"),
    ("futon", "energy", 5, "sleep"),
    ("kotatsu", "fullness", 5, "eat"),
])
def test_pets_use_the_new_pieces_for_what_they_are_for(name, need, value, activity):
    world, zone, pet = _home()
    for piece in list(world.furniture):                    # nothing else of that kind to choose from
        if world.definition(world.furniture[piece]).activity == activity:
            world.store(piece)
    _only(world, zone, name)
    pet.needs[need] = value
    pet.activity = None
    behaviour.decide(world, pet)
    assert pet.activity.kind == activity
    assert world.furniture[pet.activity.furniture].definition == name


@pytest.mark.parametrize("name, command", [("tv_set", "relax"), ("fireplace", "relax"),
                                           ("rocking_horse", "play"), ("telescope", "play")])
def test_asking_to_relax_or_play_can_use_the_new_pieces(name, command):
    world, zone, pet = _home()
    _only(world, zone, name)
    assert world.command(PET, command) == "accepted"
    pet.activity = None
    behaviour.decide(world, pet)
    assert pet.activity.kind == command
    assert world.furniture[pet.activity.furniture].definition == name


def test_pieces_above_the_home_level_wait_in_the_shop():
    world = World(CATALOG, "a" * 32, seed=4)
    world.add_zone("s", 0, 0, 40)
    world.ledger.apply("coins", "test", 1000)
    assert world.buy("kotatsu", "k") == "locked"
    assert world.buy("floor_lamp", "f") == "accepted"
