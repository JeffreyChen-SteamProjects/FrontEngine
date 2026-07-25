"""
PetMotion 的引導目標測試：三種行為模式都要能被導向指定點（鬼抓人用）。
Tests for PetMotion guidance — every behaviour must steer toward a given point,
which is what lets the tag game work outside floor mode.
"""
import random

from frontengine.show.pet.desktop_pet import (
    BEHAVIOUR_CHASE, BEHAVIOUR_FLOOR, BEHAVIOUR_WANDER, PetMotion,
)

BOUNDS = (0, 0, 800, 600)


def _motion(**kwargs) -> PetMotion:
    options = dict(x=0, y=0, width=64, height=64, bounds=BOUNDS, speed=4, rng=random.Random(1))
    options.update(kwargs)
    return PetMotion(**options)


def _centre(motion: PetMotion):
    return (motion.x + motion.width / 2.0, motion.y + motion.height / 2.0)


def _distance_to(motion: PetMotion, point) -> float:
    centre_x, centre_y = _centre(motion)
    return ((point[0] - centre_x) ** 2 + (point[1] - centre_y) ** 2) ** 0.5


def test_guidance_starts_unset() -> None:
    assert _motion().guidance is None


def test_floor_guidance_walks_toward_the_x() -> None:
    motion = _motion(x=100, y=536, behaviour=BEHAVIOUR_FLOOR)
    motion.set_guidance(600.0, 0.0)
    assert motion.follow_target_x == 600.0
    for _ in range(200):
        motion.step()
        if motion.follow_target_x is None:
            break
    assert motion.x + motion.width / 2 > 500


def test_guidance_defaults_its_y_to_the_current_centre() -> None:
    motion = _motion(x=0, y=200, behaviour=BEHAVIOUR_WANDER)
    motion.set_guidance(500.0)
    assert motion.guidance == (500.0, 232.0)


def test_wander_steers_toward_the_guidance_point() -> None:
    motion = _motion(x=0, y=0, behaviour=BEHAVIOUR_WANDER)
    target = (600.0, 400.0)
    motion.set_guidance(*target)
    before = _distance_to(motion, target)
    for _ in range(200):
        motion.step()
    assert _distance_to(motion, target) < before / 2


def test_wander_keeps_its_speed_while_steering() -> None:
    motion = _motion(x=0, y=0, behaviour=BEHAVIOUR_WANDER)
    motion.set_guidance(600.0, 400.0)
    for _ in range(50):
        motion.step()
        speed = (motion.vx ** 2 + motion.vy ** 2) ** 0.5
        assert abs(speed - motion.speed) < 1e-6


def test_wander_stays_inside_the_bounds_while_guided() -> None:
    motion = _motion(x=0, y=0, behaviour=BEHAVIOUR_WANDER)
    motion.set_guidance(5000.0, -5000.0)  # far outside the screen
    for _ in range(300):
        x, y = motion.step()
        assert BOUNDS[0] <= x <= BOUNDS[2] - motion.width
        assert BOUNDS[1] <= y <= BOUNDS[3] - motion.height


def test_unguided_wander_is_unchanged() -> None:
    motion = _motion(x=100, y=100, behaviour=BEHAVIOUR_WANDER)
    velocity = (motion.vx, motion.vy)
    motion.step()
    assert (motion.vx, motion.vy) == velocity, "no guidance means no steering"


def test_chase_guidance_wins_over_the_cursor() -> None:
    motion = _motion(x=0, y=0, behaviour=BEHAVIOUR_CHASE)
    motion.set_target(10.0, 10.0)        # the cursor, right next to the pet
    motion.set_guidance(700.0, 500.0)    # the playmate, far away
    for _ in range(200):
        motion.step()
    assert _distance_to(motion, (700.0, 500.0)) < 20
    assert motion.asleep is False, "reaching a playmate is not a nap"


def test_chase_without_guidance_still_naps_on_the_cursor() -> None:
    motion = _motion(x=0, y=0, behaviour=BEHAVIOUR_CHASE)
    motion.set_target(60.0, 60.0)
    for _ in range(60):
        motion.step()
    assert motion.asleep is True


def test_clearing_guidance_releases_the_pet() -> None:
    motion = _motion(behaviour=BEHAVIOUR_FLOOR)
    motion.set_guidance(600.0, 0.0)
    motion.clear_guidance()
    assert motion.guidance is None
    assert motion.follow_target_x is None


def test_guidance_is_accepted_for_every_behaviour() -> None:
    for behaviour in (BEHAVIOUR_FLOOR, BEHAVIOUR_WANDER, BEHAVIOUR_CHASE):
        motion = _motion(behaviour=behaviour)
        motion.set_guidance(300.0, 300.0)
        assert motion.guidance == (300.0, 300.0)
        motion.step()  # must not raise in any mode
