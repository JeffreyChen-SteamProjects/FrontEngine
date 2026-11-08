"""Every piece a pet could plausibly use has a use, and pieces show their own pose first."""
from types import SimpleNamespace

import pytest

from frontengine.show.pet.inkside.cast import TEMPLATES
from frontengine.show.pet.inkside.sprite_sheet import HOME_POSE_MS, SPRITES
from frontengine.show.pet_game.resident_art import semantic_action
from frontengine.utils.pet_game import simulation
from frontengine.utils.pet_game.catalog import POSES, builtin_catalog
from frontengine.utils.pet_game.world import furniture_item
from frontengine.utils.pet_game.resident import Activity
from frontengine.utils.pet_game.world import World
from frontengine.utils.pet_pack.layered import HOME_POSES

PET = "b" * 32
# Lights, plants and the rug are looked at; the stairs help pets climb onto raised pieces.
LOOK_ONLY = {"plant_pot", "wall_lamp", "rug", "string_lights", "floor_lamp", "hanging_plants", "pet_stairs"}
OWN_POSES = {"bookshelf": "read", "piano": "music", "easel": "paint", "aquarium": "watch",
             "grandfather_clock": "watch", "tv_set": "watch", "fireplace": "watch", "telescope": "watch",
             "bath_tub": "bathe", "shower": "bathe", "wardrobe_closet": "dress"}


def test_only_lights_plants_rug_and_stairs_have_no_use():
    catalog = builtin_catalog()
    assert {name for name, definition in catalog.furniture.items() if definition.activity is None} == LOOK_ONLY


@pytest.mark.parametrize("piece, pose", sorted(OWN_POSES.items()))
def test_pieces_ask_for_their_own_pose_first(piece, pose):
    definition = builtin_catalog().furniture[piece]
    assert definition.poses[0] == pose
    assert pose in POSES and pose in HOME_POSES


@pytest.mark.parametrize("pose", sorted(set(OWN_POSES.values())))
def test_every_builtin_character_has_a_drawn_loop_for_each_new_pose(pose):
    assert pose in HOME_POSE_MS
    for template in TEMPLATES:
        name = template.ident.removeprefix("inkside-")
        assert (SPRITES / f"inkside-{name}-{pose}.png").is_file(), (template.ident, pose)
        assert f"{pose}_sprite" in template.sprite_actions


def _home_with(piece: str) -> World:
    world = World(builtin_catalog(), "c" * 32, seed=5)
    world.automatic = False
    zone = world.add_zone("screen", 0, 900, 40)
    world.grant_starter_kit()
    for name, cell in (("bed_basic", 2), ("table_basic", 7), ("desk_basic", 12)):
        assert world.place(name, zone, cell)[0] == "accepted"
    assert world.ledger.apply("gift-" + piece, "test", 0, {furniture_item(piece): 1}) == "accepted"
    assert world.place(piece, zone, 20)[0] == "accepted"
    assert world.add_resident({"id": PET, "name": "Mochi", "mood": 40, "fullness": 80, "affection": 3,
                               "energy": 80}, zone) == "accepted"
    world.residents[PET].traits = ()
    return world


@pytest.mark.parametrize("piece, command", [("easel", "play"), ("aquarium", "relax"),
                                            ("grandfather_clock", "relax"), ("wardrobe_closet", "relax")])
def test_residents_now_use_the_former_decorations(piece, command):
    world = _home_with(piece)
    assert world.command(PET, command) == "accepted"
    for _ in range(2000):
        simulation.step(world)
        activity = world.residents[PET].activity
        if activity is not None and activity.phase != "moving":
            break
    activity = world.residents[PET].activity
    assert activity.kind == command
    assert world.furniture[activity.furniture].definition == piece
    assert activity.phase != "moving"


class _Renderer:
    def __init__(self, actions):
        self.actions = set(actions)

    def has_action(self, action):
        return action in self.actions


def _using(piece: str):
    catalog = builtin_catalog()
    definition = catalog.furniture[piece]
    world = SimpleNamespace(furniture={"f1": SimpleNamespace(definition=piece)},
                            definition=lambda _piece: definition)
    kind = {"wash": "wash"}.get(definition.activity, definition.activity)
    return world, SimpleNamespace(activity=Activity(kind, "", furniture="f1", phase="using"))


@pytest.mark.parametrize("piece, own", [("bookshelf", "read"), ("piano", "music"), ("bath_tub", "bathe"),
                                        ("wardrobe_closet", "dress")])
def test_a_drawn_pose_wins_and_a_dressed_pet_falls_back(piece, own):
    world, resident = _using(piece)
    undressed = _Renderer({"idle", "sit", "play", "greet", own})
    assert semantic_action(resident, world, undressed) == own
    dressed = _Renderer({"idle", "sit", "play", "greet"})
    assert semantic_action(resident, world, dressed) in {"sit", "play", "greet"}
    assert semantic_action(resident, world, _Renderer({"idle"})) == "idle"
