"""Rigged home poses: built-in characters work, eat and sleep in their own layered loops, dressed or not."""
import copy
from types import SimpleNamespace

import pytest

from frontengine.show.pet.asset_library import PetAssetLibrary
from frontengine.show.pet.inkside.library import VERSION, install_builtin, upgrade_builtin
from frontengine.show.pet.wardrobe import WardrobeDraft
from frontengine.show.pet_game.home_service import HomeService
from frontengine.show.pet_game.resident_art import PROFESSION_ACTIONS, ResidentArt, semantic_action
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.resident import Activity
from frontengine.utils.pet_pack.layered import ACTIONS, HOME_POSES, LEGACY_SPRITE_ACTIONS, OPTIONAL_ACTIONS
from test_pet_home_art import _wait

APPEARANCE = {"character": {"id": "inkside-mochi", "version": "1"},
              "equipped": {"head": {"id": "inkside-mochi-work-cap", "version": "1"}, "body": None},
              "colors": {"inkside-mochi@1": {"coat": "#123456"}, "someone-elses-cat@1": {"fur": "#654321"}},
              "variants": {}}


def test_every_home_pose_is_a_layered_action_and_old_whole_body_names_stay_readable():
    assert set(HOME_POSES) <= set(ACTIONS) | set(OPTIONAL_ACTIONS)
    assert not set(OPTIONAL_ACTIONS) & set(ACTIONS)
    assert {pose + "_sprite" for pose in HOME_POSES} <= set(LEGACY_SPRITE_ACTIONS)


def test_older_builtin_references_move_to_the_current_version_and_keep_the_rest():
    upgraded = upgrade_builtin(APPEARANCE)
    assert upgraded["character"] == {"id": "inkside-mochi", "version": VERSION}
    assert upgraded["equipped"] == {"head": {"id": "inkside-mochi-work-cap", "version": VERSION}, "body": None}
    assert upgraded["colors"] == {f"inkside-mochi@{VERSION}": {"coat": "#123456"},
                                  "someone-elses-cat@1": {"fur": "#654321"}}
    assert APPEARANCE["character"]["version"] == "1"                    # the input is not mutated
    assert upgrade_builtin(upgraded) is None


@pytest.mark.parametrize("character", [
    {"id": "inkside-mochi", "version": VERSION}, {"id": "someone-elses-cat", "version": "1"},
    {"id": "inkside-mochi", "version": "beta"}, None,
])
def test_current_third_party_and_odd_references_are_left_alone(character):
    assert upgrade_builtin({**APPEARANCE, "character": character, "equipped": {}, "colors": {}}) is None


class _Renderer:
    def __init__(self, actions):
        self.actions = set(actions)

    def has_action(self, action):
        return action in self.actions


def _working(recipe):
    world = SimpleNamespace(tasks={"t1": SimpleNamespace(recipe=recipe)}, catalog=builtin_catalog())
    resident = SimpleNamespace(activity=Activity("work", "", task="t1", phase="using"))
    return world, resident


@pytest.mark.parametrize("recipe, pose", [("letter", "write"), ("herbs", "garden"), ("toy", "craft")])
def test_work_uses_the_profession_pose_when_the_character_has_it(recipe, pose):
    world, resident = _working(recipe)
    assert semantic_action(resident, world, _Renderer(PROFESSION_ACTIONS.values())) == pose
    assert semantic_action(resident, world, _Renderer({"sit"})) == "sit"          # dressed or third-party
    assert semantic_action(resident) == "sit"


def test_work_without_a_known_task_sits():
    world, resident = _working("letter")
    resident.activity = Activity("work", "", task="gone", phase="using")
    assert semantic_action(resident, world, _Renderer({"write"})) == "sit"


@pytest.fixture(scope="module")
def library(tmp_path_factory):
    library = PetAssetLibrary(tmp_path_factory.mktemp("library"))
    install_builtin(library, "inkside-mochi")
    return library


def test_builtin_renderers_have_the_home_poses_dressed_or_not(library):
    catalog, _ = library.scan()
    character = catalog.resolve({"id": "inkside-mochi", "version": VERSION}, "character")
    assert set(HOME_POSES) <= set(character.actions)
    assert not {action for action in character.actions if action.endswith("_sprite")}
    bare = catalog.prepare({"character": {"id": "inkside-mochi", "version": VERSION}, "equipped": {}})
    assert all(bare.has_action(pose) for pose in HOME_POSES)
    cap = {"id": "inkside-mochi-work-cap", "version": VERSION}
    dressed = catalog.prepare({"character": {"id": "inkside-mochi", "version": VERSION}, "equipped": {"head": cap}})
    assert all(dressed.has_action(pose) for pose in HOME_POSES)


def test_a_resident_wearing_an_older_builtin_is_upgraded_through_a_checked_change(tmp_path, library, *, home_store_factory, lifetime_factory):
    lifetime = lifetime_factory()
    profiles = PetProfiles({}, lambda: None)
    service = HomeService(None, home_store_factory(tmp_path, builtin_catalog()), profiles)
    service.create_home("screen", 0, 900, 40, seed=3)
    record = profiles.create("Mochi")
    assert service.adopt(record["id"]) == "accepted"
    old = copy.deepcopy(profiles.get(record["id"])["appearance"])
    old["character"] = {"id": "inkside-mochi", "version": "1"}
    profiles.update(record["id"], {"appearance": old})
    art = ResidentArt(service, library_factory=lambda: library, lifetime=lifetime)
    try:
        changed = []
        art.changed.connect(lambda: changed.append(True))
        assert art.renderer(record["id"]) is None
        _wait(lambda: changed, timeout=60)
        saved = profiles.get(record["id"])["appearance"]
        assert saved["character"] == {"id": "inkside-mochi", "version": VERSION}
        renderer = art.renderer(record["id"])
        assert renderer is not None
        assert renderer.has_action("garden")
        assert service.sessions[record["id"]].appearance_renderer is renderer
    finally:
        art.shutdown()
        service.shutdown()


def test_wardrobe_offers_the_current_builtin_version(library):
    profiles = PetProfiles({}, lambda: None)
    record = profiles.create("Mochi")
    catalog, _ = library.scan()
    draft = WardrobeDraft(profiles, record["id"], catalog)
    draft.choose_character({"id": "inkside-mochi", "version": VERSION})
    draft.apply()
    assert profiles.get(record["id"])["appearance"]["character"]["version"] == VERSION


def test_an_upgraded_recoloured_builtin_still_prepares(library):
    catalog, _ = library.scan()
    old = {"character": {"id": "inkside-mochi", "version": "1"}, "equipped": {},
           "colors": {"inkside-mochi@1": {"coat": "#00a080"}}, "variants": {}}
    renderer = catalog.prepare(upgrade_builtin(old))
    assert renderer is not None
    assert all(renderer.has_action(pose) for pose in HOME_POSES)      # recoloured: same rigged poses
