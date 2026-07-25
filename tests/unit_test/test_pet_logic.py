"""
桌面寵物的純邏輯測試（不建立任何 widget，因此不需要 QApplication）：
移動模型、心情／飽足／成長、台詞挑選、動作包掃描與音訊脈動換算。

Pure-logic tests for the desktop pet — no widgets are created, so no
QApplication is needed: the motion model, mood/hunger/growth, chatter picking,
pet-pack scanning and the audio pulse mapping.
"""
import random

from frontengine.show.pet.desktop_pet import (
    BEHAVIOUR_FLOOR, BEHAVIOUR_WANDER, PetGrowth, PetHunger, PetMood, PetMotion, PetTimeline,
    STATE_CLIMB, STATE_DRAG, STATE_FALL, STATE_IDLE, STATE_SLEEP, STATE_WALK, SURFACE_CEILING,
    SURFACE_FLOOR, SURFACE_LEFT, audio_pulse_scale, derive_visual_state, format_status,
    message_bucket, nearest_peer, parse_timeline, pick_message, pop_due_reminders, scan_pet_pack,
    size_for_level,
)

BOUNDS = (0, 0, 800, 600)


def _motion(**kwargs) -> PetMotion:
    options = dict(x=0, y=0, width=64, height=64, bounds=BOUNDS, speed=4, rng=random.Random(1))
    options.update(kwargs)
    return PetMotion(**options)


# --- motion ---------------------------------------------------------------
def test_gravity_lands_on_the_floor() -> None:
    motion = _motion(y=0, behaviour=BEHAVIOUR_FLOOR)
    for _ in range(200):
        motion.step()
    assert motion.y + motion.height <= BOUNDS[3]
    assert not motion._airborne


def test_walking_stays_inside_the_bounds() -> None:
    motion = _motion(behaviour=BEHAVIOUR_FLOOR, climb=False)
    for _ in range(500):
        x, _y = motion.step()
        assert BOUNDS[0] <= x <= BOUNDS[2] - motion.width


def test_wander_bounces_off_every_edge() -> None:
    motion = _motion(behaviour=BEHAVIOUR_WANDER)
    for _ in range(500):
        x, y = motion.step()
        assert BOUNDS[0] <= x <= BOUNDS[2] - motion.width
        assert BOUNDS[1] <= y <= BOUNDS[3] - motion.height


def test_throw_makes_it_airborne_then_it_settles() -> None:
    motion = _motion(behaviour=BEHAVIOUR_FLOOR)
    motion.throw(6.0, -12.0)
    assert motion._airborne
    for _ in range(400):
        motion.step()
    assert not motion._airborne


def test_grab_nearest_wall_only_near_an_edge() -> None:
    middle = _motion(x=400)
    assert middle.grab_nearest_wall() is False
    edge = _motion(x=5)
    assert edge.grab_nearest_wall() is True
    assert edge.surface == SURFACE_LEFT


def test_climbing_is_opt_out() -> None:
    motion = _motion(x=5, climb=False)
    assert motion.grab_nearest_wall() is False


def test_follow_target_walks_toward_it_then_clears() -> None:
    motion = _motion(x=100)
    motion.set_follow(300.0)
    for _ in range(200):
        motion.step()
        if motion.follow_target_x is None:
            break
    assert motion.follow_target_x is None
    assert 200 < motion.x + motion.width / 2 < 400


def test_platform_walking_turns_at_the_span_edges() -> None:
    motion = _motion(x=200, y=236)
    motion.set_platforms([(200.0, 400.0, 300.0)])
    motion.on_platform = True
    motion.ground_feet = 300.0
    motion.surface = SURFACE_FLOOR
    for _ in range(300):
        motion.step()
        assert 200.0 <= motion.x <= 400.0 - motion.width


def test_platform_vanishing_drops_the_pet() -> None:
    motion = _motion(x=200, y=236)
    motion.on_platform = True
    motion.ground_feet = 300.0
    motion.set_platforms([])
    motion.step()
    assert motion.on_platform is False


def test_sleep_and_wake() -> None:
    motion = _motion()
    motion.sleep()
    assert motion.state == STATE_SLEEP
    motion.wake()
    assert motion.state == STATE_WALK


# --- visual state ---------------------------------------------------------
def test_derive_visual_state_priority() -> None:
    assert derive_visual_state(True, True, SURFACE_FLOOR, STATE_WALK) == STATE_DRAG
    assert derive_visual_state(False, True, SURFACE_FLOOR, STATE_WALK) == STATE_FALL
    assert derive_visual_state(False, False, SURFACE_CEILING, STATE_WALK) == STATE_CLIMB
    assert derive_visual_state(False, False, SURFACE_FLOOR, STATE_SLEEP) == STATE_SLEEP
    assert derive_visual_state(False, False, SURFACE_FLOOR, "idle") == STATE_IDLE
    assert derive_visual_state(False, False, SURFACE_FLOOR, STATE_WALK) == STATE_WALK


# --- mood / hunger / growth ----------------------------------------------
def test_mood_buckets_and_clamps() -> None:
    assert PetMood(200).value == 100
    assert PetMood(-5).value == 0
    assert PetMood("bad").value == 60
    assert PetMood(90).level() == PetMood.HAPPY
    assert PetMood(50).level() == PetMood.CONTENT
    assert PetMood(10).level() == PetMood.SAD


def test_hunger_feeding_and_decay() -> None:
    hunger = PetHunger(20)
    assert hunger.level() == PetHunger.HUNGRY
    hunger.feed()
    assert hunger.value == 50
    assert hunger.level() == PetHunger.OK
    hunger.feed()
    assert hunger.level() == PetHunger.FULL
    for _ in range(200):
        hunger.decay()
    assert hunger.value == 0


def test_growth_levels_up_on_thresholds() -> None:
    growth = PetGrowth(0)
    assert growth.level() == 1
    assert growth.add(100) is True
    assert growth.level() == 2
    assert growth.add(1) is False
    assert PetGrowth(-10).affection == 0


def test_size_grows_with_level_but_is_capped() -> None:
    assert size_for_level(100, 1) == 100
    assert size_for_level(100, 2) == 108
    assert size_for_level(100, 99) == 150
    assert size_for_level(1, 1) >= 16


def test_format_status_uses_labels() -> None:
    labels = {"level": "Lv.", PetMood.HAPPY: "happy", PetHunger.FULL: "full"}
    assert format_status(3, PetMood.HAPPY, PetHunger.FULL, labels) == "Lv.3 · happy · full"


# --- chatter --------------------------------------------------------------
def test_message_bucket_covers_the_clock() -> None:
    assert message_bucket(8) == "morning"
    assert message_bucket(14) == "afternoon"
    assert message_bucket(20) == "evening"
    assert message_bucket(2) == "night"
    assert message_bucket(26) == "night"  # 26 wraps to 02:00


def test_pick_message_prefers_mood_then_time_then_generic() -> None:
    messages = {"happy": ["mood"], "morning": ["time"], "any": ["generic"]}
    assert pick_message(8, random.Random(0), messages, mood="happy") in ("mood", "time", "generic")
    assert pick_message(8, random.Random(0), {"morning": ["time"]}) == "time"
    assert pick_message(8, random.Random(0), {"any": ["generic"]}) == "generic"
    assert pick_message(8, random.Random(0), {}) == ""


# --- timeline / reminders / peers ----------------------------------------
def test_parse_timeline_skips_malformed_entries() -> None:
    events = parse_timeline([{"at": 1, "say": "hi"}, {"say": "no at"}, "junk", {"at": "x"}])
    assert len(events) == 1


def test_timeline_pops_events_in_order_once() -> None:
    timeline = PetTimeline([(2, {"say": "b"}), (1, {"say": "a"})])
    assert [event["say"] for event in timeline.pop_due(1.5)] == ["a"]
    assert [event["say"] for event in timeline.pop_due(3)] == ["b"]
    assert timeline.pop_due(9) == []
    timeline.reset()
    assert len(timeline.pop_due(9)) == 2


def test_pop_due_reminders_splits_on_now() -> None:
    due, remaining = pop_due_reminders(10, [(5, "past"), (15, "future")])
    assert [text for _when, text in due] == ["past"]
    assert [text for _when, text in remaining] == ["future"]


def test_nearest_peer_picks_the_closest() -> None:
    peer, distance = nearest_peer((0, 0), [(30, 40), (3, 4)])
    assert peer == (3, 4)
    assert distance == 5
    assert nearest_peer((0, 0), []) == (None, float("inf"))


# --- pet packs ------------------------------------------------------------
def test_scan_pet_pack_maps_aliases(tmp_path) -> None:
    (tmp_path / "run.png").write_bytes(b"x")
    (tmp_path / "sit.gif").write_bytes(b"x")
    (tmp_path / "notes.txt").write_bytes(b"x")
    pack = scan_pet_pack(str(tmp_path))
    assert set(pack) == {STATE_WALK, STATE_IDLE}


def test_scan_pet_pack_tolerates_bad_input(tmp_path) -> None:
    assert scan_pet_pack(str(tmp_path / "missing")) == {}
    assert scan_pet_pack(str(tmp_path / "file.png")) == {}


# --- audio pulse ----------------------------------------------------------
def test_audio_pulse_scale_maps_and_clamps() -> None:
    assert audio_pulse_scale(0.0) == 0.7
    assert audio_pulse_scale(1.0) == 1.0
    assert audio_pulse_scale(0.5) == 0.85
    assert audio_pulse_scale(9.0) == 1.0
    assert audio_pulse_scale(-9.0) == 0.7
    assert audio_pulse_scale("loud") == 1.0
