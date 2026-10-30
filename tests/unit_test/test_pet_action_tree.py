"""In the default "cycle all actions" mode a free pet picks its next action at random from the whole set."""
import random
from collections import Counter

import pytest

from frontengine.show.pet.desktop_pet import (
    AUTONOMOUS_ACTIONS, BEHAVIOUR_ACTIONS, BEHAVIOUR_FLOOR, POSE_STATES, SURFACE_FLOOR, SURFACE_LEFT, SURFACE_RIGHT,
    PetMotion, derive_visual_state,
)

BOUNDS = (0, 0, 800, 600)


def _floor_pet(seed=3, behaviour=BEHAVIOUR_ACTIONS, **options):
    motion = PetMotion(x=300, y=600 - 64, width=64, height=64, bounds=BOUNDS, speed=4,
                       rng=random.Random(seed), behaviour=behaviour, **options)
    motion.surface = SURFACE_FLOOR
    return motion


def _picks(motion, count=2000):
    seen = Counter()
    for _ in range(count):
        motion._idle_count = 0
        motion._new_state()
        seen['climb' if motion._seek_wall else motion.state] += 1
    return seen


def test_every_action_of_the_tree_is_chosen_in_proportion():
    seen = _picks(_floor_pet())
    assert set(seen) == {name for name, *_ in AUTONOMOUS_ACTIONS}
    total = sum(weight for _name, weight, *_ in AUTONOMOUS_ACTIONS)
    for name, weight, *_ in AUTONOMOUS_ACTIONS:
        assert abs(seen[name] / 2000 - weight / total) < 0.04, name


def test_climbing_is_only_chosen_when_allowed_and_off_ledges():
    assert 'climb' not in _picks(_floor_pet(climb=False))
    ledge = _floor_pet()
    ledge.on_platform = True
    assert 'climb' not in _picks(ledge)


@pytest.mark.parametrize('x, wall', [(40, SURFACE_LEFT), (700, SURFACE_RIGHT)])
def test_climb_walks_to_the_nearer_wall_and_climbs_it(monkeypatch, x, wall):
    motion = _floor_pet()
    motion.x = float(x)
    monkeypatch.setattr(motion._rng, 'choices', lambda options, weights: [('climb', 6, 0, 0)])
    motion._new_state()
    assert motion.state == 'walk' and motion._seek_wall
    for _ in range(400):
        motion.step()
        if motion.surface != SURFACE_FLOOR:
            break
    assert motion.surface == wall


@pytest.mark.parametrize('pose', sorted(POSE_STATES))
def test_poses_hold_still_for_their_duration_and_show_their_animation(monkeypatch, pose):
    motion = _floor_pet()
    entry = next(item for item in AUTONOMOUS_ACTIONS if item[0] == pose)
    monkeypatch.setattr(motion._rng, 'choices', lambda options, weights: [entry])
    motion._new_state()
    ticks = motion._state_ticks
    assert entry[2] <= ticks <= entry[3]
    start = motion.x
    for _ in range(ticks):
        motion.step()
        assert motion.x == start and motion.state == pose
        assert derive_visual_state(False, False, motion.surface, motion.state) == pose


def test_groom_lasts_its_three_second_animation():
    entry = next(item for item in AUTONOMOUS_ACTIONS if item[0] == 'groom')
    assert entry[2] == entry[3] == 91   # 91 ticks x 33 ms ~ 3000 ms


def test_two_idles_in_a_row_still_lead_to_sleep(monkeypatch):
    motion = _floor_pet()
    monkeypatch.setattr(motion._rng, 'choices', lambda options, weights: [('idle', 14, 20, 80)])
    motion._new_state()
    motion._new_state()
    motion._new_state()
    assert motion.state == 'sleep'


def test_the_actions_mode_is_the_floor_mode_with_random_actions():
    motion = _floor_pet()
    assert motion.behaviour == BEHAVIOUR_FLOOR and motion.random_actions and motion.mode == BEHAVIOUR_ACTIONS
    motion.behaviour = BEHAVIOUR_FLOOR
    assert not motion.random_actions and motion.mode == BEHAVIOUR_FLOOR


def test_plain_floor_mode_only_walks_idles_and_sleeps():
    assert set(_picks(_floor_pet(behaviour=BEHAVIOUR_FLOOR))) <= {'walk', 'idle'}


def test_cycling_all_actions_is_the_default_everywhere(tmp_path):
    from frontengine.ui.page.pet.pet_setting_ui import PetSettingUI
    from frontengine.user_setting.pet_profile_schema import presentation_defaults
    assert presentation_defaults()['behaviour'] == BEHAVIOUR_ACTIONS
    page = PetSettingUI()
    try:
        assert page.behaviour_combobox.currentData() == BEHAVIOUR_ACTIONS
        assert page.customization_defaults()['behaviour'] == BEHAVIOUR_ACTIONS
    finally:
        page.close()


def test_a_summoned_pet_sets_off_walking_at_once(tmp_path):
    from frontengine.show.pet.desktop_pet import DesktopPetWidget
    from frontengine.user_setting.pet_profiles import PetProfiles
    from test_pet_profile_sessions import _sprite
    for seed in range(8):
        pet = DesktopPetWidget(_sprite(tmp_path), behaviour=BEHAVIOUR_ACTIONS, sit_on_windows=False,
                               profiles=PetProfiles({}, lambda: None))
        try:
            pet.motion._rng = random.Random(seed)
            pet.start_moving((0, 0, 800, 600))
            assert pet.motion.state == 'walk' and pet.motion._state_ticks >= 30
            start = pet.motion.x
            for _ in range(10):
                pet.motion.step()
            assert pet.motion.x != start
        finally:
            pet.close()


def test_a_pet_keeps_the_chosen_mode_through_its_own_presentation_defaults(tmp_path):
    from frontengine.show.pet.desktop_pet import DesktopPetWidget
    from frontengine.user_setting.pet_profiles import PetProfiles
    from test_pet_profile_sessions import _sprite
    pet = DesktopPetWidget(_sprite(tmp_path), behaviour=BEHAVIOUR_ACTIONS, sit_on_windows=False,
                           profiles=PetProfiles({}, lambda: None))
    try:
        pet._apply_customization()
        assert pet._presentation_defaults['behaviour'] == BEHAVIOUR_ACTIONS
        assert pet.motion.random_actions
    finally:
        pet.close()

