"""A free sprite pet picks what to do next at random from the whole action set."""
import random
from collections import Counter

import pytest

from frontengine.show.pet.desktop_pet import (
    AUTONOMOUS_ACTIONS, POSE_STATES, SURFACE_FLOOR, SURFACE_LEFT, SURFACE_RIGHT, PetMotion, derive_visual_state,
)

BOUNDS = (0, 0, 800, 600)


def _floor_pet(seed=3, **options):
    motion = PetMotion(x=300, y=600 - 64, width=64, height=64, bounds=BOUNDS, speed=4,
                       rng=random.Random(seed), **options)
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
