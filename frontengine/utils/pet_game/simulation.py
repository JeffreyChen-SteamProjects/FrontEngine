"""Fixed-step world time: needs, walking, using furniture and settling work.

The world advances in 200 ms steps (5 Hz) from accumulated effective time,
never from paint frames, so a slow renderer cannot change earnings and the same
seed plus the same commands always replays to the same state.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from frontengine.utils.pet_game.behaviour import (
    LOW_HYGIENE, URGENT_ENERGY, URGENT_FULLNESS, cancel_activity, decide, greet_arrived, greet_completed, help_completed,
    tag_completed,
    helpers, release,
    shared_completed, together,
)
from frontengine.utils.pet_game import goals
from frontengine.utils.pet_game.resident import PROFESSION_TRAITS
from frontengine.utils.pet_game.resident import Resident
from frontengine.utils.pet_game.schedule import block_at, game_hour

if TYPE_CHECKING:
    from frontengine.utils.pet_game.world import World

STEP_MS = 200
COME_WAIT_MS = 8000                 # how long a called pet waits where it was called to
WALK_MILLI_PER_MS = 64           # 64 logical pixels per second
MAX_ADVANCE_MS = 6 * 60 * 60 * 1000
BASE_RATES = {"energy": -1, "fullness": -2, "mood": -1, "comfort": -1, "social": -1, "hygiene": -1}
LOW_COMFORT = 30                    # below this, discomfort wears on mood
TOGETHER_SOCIAL = 20                # per minute while sharing a table or a toy box with others
LIKED_WORK_MOOD = 2                 # per minute while doing work the pet likes
FLOOR_RATES = {"nap": {"energy": 12, "mood": 0}, "snack": {"fullness": 30, "mood": 1},
               "tidy": {"hygiene": 20, "mood": 0}}       # tidying itself up: slower than a bath tub
PLAY_HYGIENE = -2                   # per minute while playing: games are messy
WASH_MIN_MS = 10000
# Mood while doing something that is not furniture-driven (absolute points/minute).
ACTIVITY_MOOD = {"wander": 2, "eat": 5, "sleep": 1}
HERB_MEAL_MOOD = 6                  # extra mood per minute when a meal uses herbs from storage
SLOW_WORK_ENERGY = 30
SLOW_WORK_MOOD = 20
BREAK_MS = (3000, 6000)


def advance(world: World, milliseconds: int) -> int:
    """Run whole steps for this much effective time; returns the number of steps."""
    if type(milliseconds) is not int or not 0 <= milliseconds <= MAX_ADVANCE_MS:
        raise ValueError("Elapsed time must be a bounded nonnegative integer")
    world.carry_ms += milliseconds
    steps = 0
    while world.carry_ms >= STEP_MS:
        world.carry_ms -= STEP_MS
        step(world)
        steps += 1
    return steps


def step(world: World) -> None:
    world.time_ms += STEP_MS
    for identifier in sorted(world.residents):
        resident = world.residents[identifier]
        if resident.parked or resident.away:
            continue
        _apply_needs(world, resident)
        _act(world, resident)
    goals.update(world)


def _rates(world: World, resident: Resident) -> dict[str, int]:
    rates = dict(BASE_RATES)
    rates["comfort"] += world.comfort(resident.zone) // 5
    if resident.needs["comfort"] < LOW_COMFORT:
        rates["mood"] -= 1
    if resident.needs["hygiene"] < LOW_HYGIENE:
        rates["mood"] -= 1
    if "social" in resident.traits:
        rates["social"] -= 1
    activity = resident.activity
    if activity is not None and activity.phase == "using":
        _activity_rates(world, resident, rates)
    return rates


def _activity_rates(world: World, resident: Resident, rates: dict[str, int]) -> None:
    """What the current activity adds to or replaces in the base rates."""
    activity = resident.activity
    if activity.kind in ACTIVITY_MOOD:
        rates["mood"] = ACTIVITY_MOOD[activity.kind]
    if activity.kind in ("play", "tag"):
        rates["hygiene"] = PLAY_HYGIENE
    if activity.kind in FLOOR_RATES:
        rates.update(FLOOR_RATES[activity.kind])
    elif activity.kind == "work":
        recipe = world.catalog.recipes[world.tasks[activity.task].recipe]
        rates["energy"] = -recipe.energy_per_minute
        if PROFESSION_TRAITS[recipe.profession] in resident.traits:
            rates["mood"] += LIKED_WORK_MOOD
    elif activity.furniture is not None:
        definition = world.definition(world.furniture[activity.furniture])
        for need, rate in definition.effects.items():
            rates[need] = rates[need] + rate if need == "mood" else rate
    if activity.bonus:
        rates["mood"] += HERB_MEAL_MOOD
    if together(world, resident):
        rates["social"] += TOGETHER_SOCIAL


def _apply_needs(world: World, resident: Resident) -> None:
    """Integer points per minute, accumulated exactly across steps."""
    for need, rate in _rates(world, resident).items():
        total = resident.accumulators.get(need, 0) + rate * STEP_MS
        whole = total // 60000 if total >= 0 else -((-total) // 60000)
        resident.accumulators[need] = total - whole * 60000
        if whole:
            resident.needs[need] = max(0, min(100, resident.needs[need] + whole))


def _act(world: World, resident: Resident) -> None:
    activity = resident.activity
    if activity is None:
        if world.time_ms >= resident.decide_after_ms:
            decide(world, resident)
        return
    if activity.kind == "drag":
        return
    if activity.phase == "moving":
        _walk(world, resident)
        return
    if _interrupted_by_need(world, resident):
        return
    if activity.kind == "work":
        _work(world, resident)
    elif _finished(world, resident):
        finish(world, resident)


def _walk(world: World, resident: Resident) -> None:
    activity = resident.activity
    distance = activity.target_x - resident.x_milli
    reach = WALK_MILLI_PER_MS * STEP_MS
    if distance:
        resident.facing = 1 if distance > 0 else -1
    if abs(distance) > reach:
        resident.x_milli += reach * resident.facing
        return
    resident.x_milli = activity.target_x
    if activity.kind == "visit":
        resident.activity = None
        world.cross(resident.identifier)
        resident.decide_after_ms = world.time_ms
        return
    activity.phase = "using"
    activity.started_ms = world.time_ms
    if activity.until_ms is not None:
        activity.until_ms = max(activity.until_ms, world.time_ms + 1000)
    if activity.kind == "come":               # called over: the wait starts once it is there
        activity.until_ms = world.time_ms + COME_WAIT_MS
    if activity.task is not None:
        world.tasks[activity.task].state = "working"
    if activity.kind == "eat":
        _season_meal(world, resident)
    if activity.kind == "greet" and activity.partner is not None:
        greet_arrived(world, resident)


def _season_meal(world: World, resident: Resident) -> None:
    """Sitting down at a table uses one herb from storage, when there is one, for a happier meal."""
    if world.ledger.available("herb") <= 0:
        return
    transaction = f"meal:{resident.identifier[:12]}:{world.time_ms}"
    if world.ledger.apply(transaction, "meal", items={"herb": -1}) == "accepted":
        resident.activity.bonus = True


def _interrupted_by_need(world: World, resident: Resident) -> bool:
    """Exhaustion and hunger stop leisure and work; they never stop sleeping or eating."""
    activity = resident.activity
    needs = resident.needs
    if activity.kind in ("sleep", "nap", "eat", "snack"):
        return False
    if needs["energy"] <= URGENT_ENERGY or needs["fullness"] <= URGENT_FULLNESS:
        cancel = "tired" if needs["energy"] <= URGENT_ENERGY else "hungry"
        cancel_activity(world, resident, cancel)
        resident.decide_after_ms = world.time_ms
        return True
    return False


def _finished(world: World, resident: Resident) -> bool:
    activity = resident.activity
    needs = resident.needs
    if activity.kind in ("sleep", "nap"):
        sleepy = block_at(resident.routine, game_hour(world.time_ms)) == "sleep"
        return needs["energy"] >= 100 or (needs["energy"] >= 95 and not sleepy)
    if activity.kind in ("eat", "snack"):
        return needs["fullness"] >= 95 and world.time_ms - activity.started_ms >= 15000
    if activity.kind in ("wash", "tidy"):
        return needs["hygiene"] >= 95 and world.time_ms - activity.started_ms >= WASH_MIN_MS
    return activity.until_ms is None or world.time_ms >= activity.until_ms


def finish(world: World, resident: Resident, pause_ms: int = 1000) -> None:
    """Complete normally: release furniture and decide again after a short pause."""
    activity = resident.activity
    if activity.kind in ("eat", "play", "relax"):
        shared_completed(world, resident, activity.furniture)
    release(world, resident)
    resident.activity = None
    resident.decide_after_ms = world.time_ms + pause_ms
    if activity.kind == "greet" and activity.partner is not None:
        greet_completed(world, resident, activity.partner)
    if activity.kind == "help" and activity.partner is not None:
        help_completed(world, resident, activity.partner)
    if activity.kind == "tag":
        tag_completed(world, resident, activity.partner)
    world.emit("completed", resident=resident.identifier, activity=activity.kind)


def _work(world: World, resident: Resident) -> None:
    task = world.tasks.get(resident.activity.task)
    if task is None or not task.open:
        finish(world, resident)
        return
    recipe = world.catalog.recipes[task.recipe]
    rate = STEP_MS
    if resident.needs["energy"] < SLOW_WORK_ENERGY or resident.needs["mood"] < SLOW_WORK_MOOD:
        rate //= 2
    if "diligent" in resident.traits:
        rate = rate * 11 // 10
    if PROFESSION_TRAITS[recipe.profession] in resident.traits:
        rate = rate * 11 // 10
    piece = world.furniture.get(resident.activity.furniture or "")
    if piece is not None:                       # each station level works a quarter faster
        rate = rate * (3 + world.station_level(piece.definition)) // 4
    rate = rate * (4 + helpers(world, resident)) // 4
    task.progress_ms += rate
    if task.progress_ms >= recipe.duration_ms:
        settle(world, resident, task)


def settle(world: World, resident: Resident, task) -> None:
    """Pay one finished unit exactly once, then continue, rest or close the order."""
    recipe = world.catalog.recipes[task.recipe]
    if task.inputs_reserved:
        world.ledger.release(recipe.inputs)
        task.inputs_reserved = False
    items = {**{name: -amount for name, amount in recipe.inputs.items()}, **recipe.outputs}
    transaction = task.settlement_id()
    result = world.ledger.apply(transaction, "work:" + recipe.identifier, recipe.coins, items)
    if result not in ("accepted", "duplicate"):
        task.progress_ms = recipe.duration_ms - 1
        task.state = "paused"
        finish(world, resident)
        world.emit("settle_failed", resident=resident.identifier, task=task.identifier, reason=result)
        return
    if result == "accepted":
        skills = resident.skills
        skills[recipe.profession] = skills.get(recipe.profession, 0) + recipe.experience
        world.emit("settled", resident=resident.identifier, task=task.identifier,
                   recipe=recipe.identifier, coins=recipe.coins, transaction=transaction,
                   station=resident.activity.furniture if resident.activity is not None else None)
    task.done += 1
    task.progress_ms = 0
    _after_unit(world, resident, task)


def _after_unit(world: World, resident: Resident, task) -> None:
    if task.done >= task.units:
        task.state = "settled"
        del world.tasks[task.identifier]
        finish(world, resident)
        return
    recipe = world.catalog.recipes[task.recipe]
    if not world.ledger.reserve(recipe.inputs):
        task.state = "waiting_materials"
        finish(world, resident)
        return
    task.inputs_reserved = True
    if "diligent" not in resident.traits:
        task.state = "paused"
        finish(world, resident, world.rng.randint(*BREAK_MS))
