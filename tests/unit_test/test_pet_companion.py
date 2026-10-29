"""Pet care uses active elapsed time independently of rendering and chatter."""

import pytest

from frontengine.utils.pet_companion import CompanionState
from frontengine.utils.pet_companion.stats import FOOD_EFFECTS


def test_food_rewards_only_after_completion_and_cooldown():
    pet = CompanionState({"fullness": 10, "mood": 20})
    assert pet.request("feed", "music") == "accepted"
    pet.advance(1.9)
    assert pet.hunger.value == 10
    assert pet.growth.affection == 0
    pet.advance(.1)
    assert pet.hunger.value == 10 + FOOD_EFFECTS["music"]["fullness"]
    assert pet.growth.affection == FOOD_EFFECTS["music"]["affection"]
    assert pet.request("feed") == "cooldown"
    pet.advance(29.9)
    assert pet.request("feed") == "cooldown"
    pet.advance(.1)
    assert pet.request("feed") == "accepted"


@pytest.mark.parametrize("interrupt", ["drag", "cancel", "work"])
def test_cancel_does_not_reward_or_start_cooldown(interrupt):
    pet = CompanionState({})
    before = pet.snapshot()
    pet.request("groom")
    pet.advance(2)
    if interrupt == "work":
        pet.set_mode(interrupt)
    else:
        pet.request(interrupt)
    pet.advance(4)
    assert pet.growth.affection == before["affection"]
    assert pet.mood.value == before["mood"]
    pet.request("cancel")
    assert pet.request("groom") == "accepted"


@pytest.mark.parametrize("mode,visual,energy", [("play", None, 69), ("work", "idle", 70), ("rest", "sleep", 73)])
def test_modes_survive_completed_actions(mode, visual, energy):
    pet = CompanionState({"mode": mode})
    assert pet.request("pet") == "accepted"
    assert pet.request("greet") == "busy"
    assert pet.visual_action == "pet"
    pet.advance(30)
    assert pet.mode == mode
    assert pet.visual_action == visual
    assert pet.energy == energy
    assert pet.allows_autonomy is (mode == "play")


def test_elapsed_batch_matches_fractional_steps_and_care_ignores_talk():
    batch = CompanionState({"preferences": {"talk": False}})
    split = CompanionState({"preferences": {"talk": True}})
    for pet in (batch, split):
        pet.request("play")
    batch.advance(120)
    for _ in range(1200):
        split.advance(.1)
    a, b = batch.snapshot(), split.snapshot()
    a.pop("preferences")
    b.pop("preferences")
    assert a == b
    assert a == {"mood": 66, "fullness": 66, "energy": 66, "affection": 3, "mode": "play"}
    assert batch.request("play") == split.request("play") == "accepted"


def test_snapshot_roundtrip_has_no_offline_penalty_or_appearance():
    record = {"mood": 55, "fullness": 45, "energy": 40, "affection": 20,
              "mode": "work", "preferences": {"nested": {"value": 1}},
              "appearance": {"character": "mochi"}, "last_seen": 0}
    pet = CompanionState(record)
    record["preferences"]["nested"]["value"] = 99
    snapshot = pet.snapshot()
    assert snapshot["preferences"]["nested"]["value"] == 1
    assert "appearance" not in snapshot
    restored = CompanionState(snapshot)
    assert restored.snapshot() == snapshot
    snapshot["preferences"]["nested"]["value"] = 77
    assert pet.preferences["nested"]["value"] == 1


@pytest.mark.parametrize("seconds", [-1, float("nan"), float("inf"), None, "bad"])
def test_invalid_elapsed_does_not_change_state(seconds):
    pet = CompanionState({})
    before = pet.snapshot()
    with pytest.raises(ValueError):
        pet.advance(seconds)
    assert pet.snapshot() == before


def test_invalid_record_values_and_commands():
    pet = CompanionState({"mood": float("inf"), "fullness": -5, "energy": 400,
                          "affection": float("inf"), "mode": "bad", "preferences": None})
    assert pet.snapshot() == {"mood": 60, "fullness": 0, "energy": 100,
                              "affection": 0, "mode": "play", "preferences": {}}
    assert pet.request("unknown") == "unsupported"
    assert pet.request("feed", "unknown") == "unsupported"
    assert pet.set_mode("unknown") == "unsupported"


def test_full_pet_declines_feed_without_reward():
    pet = CompanionState({"fullness": 100})
    assert pet.request("feed") == "full"
    pet.advance(2)
    assert pet.growth.affection == 0


def test_auto_rest_waits_for_action_end_and_can_be_disabled():
    pet = CompanionState({"energy": 11, "preferences": {"auto_rest": True}})
    pet.request("drag")
    pet.advance(30)
    assert pet.energy == 10
    assert pet.mode == "play"
    pet.request("cancel")
    pet.advance(0)
    assert pet.mode == "rest"
    pet.advance(30)
    assert pet.energy == 13
    manual = CompanionState({"energy": 10, "preferences": {"auto_rest": False}})
    manual.advance(30)
    assert manual.mode == "play"


def test_semantic_rewards_are_limited_and_deduplicated():
    pet = CompanionState({})
    assert pet.reward("arbitrary") == "unsupported"
    assert pet.reward("peer") == "accepted"
    assert pet.reward("peer") == "cooldown"
    assert pet.reward("tag") == "accepted"
    assert pet.reward("fetch") == "accepted"
    assert pet.growth.affection == 5
    pet.advance(30)
    assert pet.reward("peer") == "accepted"
    pet.set_mode("work")
    assert pet.reward("fetch") == "busy"
