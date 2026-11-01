"""How residents choose what to do and the select → reserve → move → use → release lifecycle.

Priority order: safety recovery, the player's direct command, urgent needs,
the daily routine, assigned work, then free activities. Every activity that
holds furniture releases it through ``cancel_activity`` or completion; nothing
else touches reservations.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from frontengine.utils.pet_game.resident import Activity, Resident
from frontengine.utils.pet_game.schedule import block_at, game_hour

if TYPE_CHECKING:
    from frontengine.utils.pet_game.world import World

URGENT_ENERGY = 15
URGENT_FULLNESS = 25
WORK_MIN_ENERGY = 25
LOW_MOOD = 30
LOW_SOCIAL = 35
GREET_MS = 2500
GREET_REACH_CELLS = 8
GREET_COOLDOWN_MS = 5 * 60 * 1000
SQUABBLE_COOLDOWN_MS = 10 * 60 * 1000
WAIT_MS = 5000
FREE_WEIGHTS = {"play": 3, "relax": 3, "wander": 4, "idle": 2, "greet": 2}
TRAIT_WEIGHTS = {"playful": {"play": 3}, "quiet": {"relax": 3, "play": -2, "greet": -1},
                 "social": {"wander": 2, "greet": 3}}
SHARED_COOLDOWN_MS = 10 * 60 * 1000


def cancel_activity(world: World, resident: Resident, reason: str) -> None:
    """Stop now without a completion reward; work keeps its progress, paused."""
    activity = resident.activity
    if activity is None:
        return
    release(world, resident)
    if activity.task is not None and activity.task in world.tasks:
        task = world.tasks[activity.task]
        if task.open:
            task.state = "paused"
    resident.activity = None
    resident.decide_after_ms = world.time_ms + 1000
    world.emit("interrupted", resident=resident.identifier, activity=activity.kind, reason=reason)


def release(world: World, resident: Resident) -> None:
    activity = resident.activity
    if activity is None or activity.furniture is None:
        return
    piece = world.furniture.get(activity.furniture)
    if piece is not None and piece.users.get(activity.point) == resident.identifier:
        del piece.users[activity.point]


def start(world: World, resident: Resident, kind: str, reason: str, furniture: str | None = None,
          point: int | None = None, task: str | None = None, duration: int | None = None) -> None:
    """Reserve the interaction point (if any) and begin walking there."""
    target = resident.x_milli
    if furniture is not None:
        piece = world.furniture[furniture]
        piece.users[point] = resident.identifier
        target = piece.point_x_milli(world.definition(piece), point)
    elif kind == "wander":
        width = world.zones[resident.zone].width_pixels
        target = world.rng.randint(0, width - 1) * 1000
    until = None if duration is None else world.time_ms + duration
    resident.activity = Activity(kind, reason, furniture, point, task, "moving", target, until,
                                 world.time_ms)
    resident.last_refusal = None
    world.emit("activity", resident=resident.identifier, activity=kind, reason=reason)


def _free_piece(world: World, resident: Resident, activity: str,
                owner_first: bool = False) -> tuple[str, int] | None:
    """Pick a free interaction point; beds prefer their owner and skip other owners' beds."""
    candidates = []
    for piece, definition in world.in_zone(resident.zone):
        if definition.activity != activity:
            continue
        if activity == "sleep" and piece.owner not in (None, resident.identifier):
            continue
        point = piece.free_point(definition)
        if point is not None:
            rank = 0 if owner_first and piece.owner == resident.identifier else 1
            candidates.append((rank, abs(piece.point_x_milli(definition, point) - resident.x_milli),
                               int(piece.identifier[1:]), piece.identifier, point))
    if not candidates:
        return None
    best = min(candidates)
    return best[3], best[4]


def _has_kind(world: World, resident: Resident, activity: str) -> bool:
    return any(definition.activity == activity for _piece, definition in world.in_zone(resident.zone))


def start_rest(world: World, resident: Resident, reason: str) -> None:
    found = _free_piece(world, resident, "sleep", owner_first=True)
    if found is None:
        start(world, resident, "nap", reason)      # resting is always possible
    else:
        start(world, resident, "sleep", reason, *found)


def start_meal(world: World, resident: Resident, reason: str) -> None:
    found = _free_piece(world, resident, "eat")
    if found is not None:
        start(world, resident, "eat", reason, *found)
    elif _has_kind(world, resident, "eat") and resident.needs["fullness"] > URGENT_FULLNESS - 10:
        squabble(world, resident, "eat")
        start(world, resident, "wait", "table_full", duration=WAIT_MS)
    else:
        start(world, resident, "snack", reason)    # basic food is always available


def _station_for(world: World, resident: Resident, task) -> tuple[str, int] | str:
    """An explicit station is honoured; otherwise any free station of the profession.

    Automatic choices are not stored on the task, so a paused order never keeps a
    desk away from other residents.
    """
    recipe = world.catalog.recipes[task.recipe]
    if task.station is not None and task.station not in world.furniture:
        task.station = None
    candidates = []
    for piece, definition in world.in_zone(resident.zone):
        if task.station is not None and piece.identifier != task.station:
            continue
        if definition.profession != recipe.profession:
            continue
        point = piece.free_point(definition)
        if point is not None:
            distance = abs(piece.point_x_milli(definition, point) - resident.x_milli)
            candidates.append((distance, int(piece.identifier[1:]), piece.identifier, point))
    if candidates:
        best = min(candidates)
        return best[2], best[3]
    if task.station is not None or any(definition.profession == recipe.profession
                                       for _piece, definition in world.in_zone(resident.zone)):
        return "station_busy"
    return "no_station"


def start_work(world: World, resident: Resident, reason: str) -> str | None:
    """Begin the most important open task; returns why not when impossible."""
    blocked = None
    for task in world.open_tasks(resident.identifier):
        recipe = world.catalog.recipes[task.recipe]
        if not task.inputs_reserved:
            if not world.ledger.reserve(recipe.inputs):
                task.state = "waiting_materials"
                blocked = blocked or "waiting_materials"
                continue
            task.inputs_reserved = True
            task.state = "reserved"
        found = _station_for(world, resident, task)
        if isinstance(found, str):
            blocked = blocked or found
            continue
        task.state = "travelling"
        start(world, resident, "work", reason, found[0], found[1], task.identifier)
        return None
    return blocked or "no_task"


def refusal(world: World, resident: Resident, command: str) -> str | None:
    """Why a direct command cannot be followed right now, or None."""
    if command == "work":
        if resident.needs["energy"] <= WORK_MIN_ENERGY:
            return "too_tired"
        if not world.open_tasks(resident.identifier):
            return "no_task"
    if command in ("play", "relax") and not _has_kind(world, resident, command):
        return "no_furniture"
    return None


def _start_free(world: World, resident: Resident, reason: str = "free_time") -> None:
    weights = dict(FREE_WEIGHTS)
    if reason == "cheer_up":
        weights["idle"] = 0
    for trait in resident.traits:
        for kind, change in TRAIT_WEIGHTS.get(trait, {}).items():
            weights[kind] = max(0, weights[kind] + change)
    choices = [(kind, weight) for kind, weight in weights.items()
               if kind in ("wander", "idle") or (kind == "greet" and _greet_partner(world, resident))
               or (kind not in ("greet", "wander", "idle") and _free_piece(world, resident, kind) is not None)]
    kind = world.rng.weighted(choices)
    if kind == "greet" and start_greet(world, resident):
        return
    if kind in ("play", "relax"):
        piece_id, point = _free_piece(world, resident, kind)
        low, high = world.definition(world.furniture[piece_id]).use_ms
        start(world, resident, kind, reason, piece_id, point, duration=world.rng.randint(low, high))
    else:
        low, high = (4000, 10000) if kind == "wander" else (3000, 8000)
        start(world, resident, kind, reason, duration=world.rng.randint(low, high))


def _follow_command(world: World, resident: Resident, command: str) -> None:
    reason = refusal(world, resident, command)
    if reason is not None:
        resident.last_refusal = reason
        world.emit("refused", resident=resident.identifier, command=command, reason=reason)
        decide(world, resident)
    elif command == "sleep":
        start_rest(world, resident, "command")
    elif command == "eat":
        start_meal(world, resident, "command")
    elif command == "work":
        start_work(world, resident, "command")
    else:
        found = _free_piece(world, resident, command)
        if found is None:
            squabble(world, resident, command)
            start(world, resident, "wait", "furniture_busy", duration=WAIT_MS)
        else:
            low, high = world.definition(world.furniture[found[0]]).use_ms
            start(world, resident, command, "command", *found, duration=world.rng.randint(low, high))


def decide(world: World, resident: Resident) -> None:
    """Choose the next activity for an idle resident."""
    zone = world.zones[resident.zone]
    resident.x_milli = max(0, min(zone.width_pixels * 1000 - 1, resident.x_milli))   # safety
    if resident.commands:
        _follow_command(world, resident, resident.commands.pop(0))
        return
    needs = resident.needs
    if needs["energy"] <= URGENT_ENERGY:
        return start_rest(world, resident, "tired")
    if needs["fullness"] <= URGENT_FULLNESS:
        return start_meal(world, resident, "hungry")
    block = block_at(resident.routine, game_hour(world.time_ms))
    if block == "sleep" and needs["energy"] < 90:
        return start_rest(world, resident, "bedtime")
    if block == "meal" and needs["fullness"] < 80:
        return start_meal(world, resident, "mealtime")
    if needs["social"] <= LOW_SOCIAL and start_greet(world, resident):
        return None
    if needs["mood"] <= LOW_MOOD:
        return _start_free(world, resident, "cheer_up")
    if block in ("work", "free") and needs["energy"] > WORK_MIN_ENERGY:
        why = start_work(world, resident, "scheduled_work")
        if why is None:
            return None
        if why not in ("no_task",):
            resident.last_refusal = why
    _start_free(world, resident)

# ----- residents together -------------------------------------------------------------

def _available(other: Resident) -> bool:
    return (not other.parked and not other.away
            and (other.activity is None or other.activity.kind in ("wander", "idle")))


def _greet_partner(world: World, resident: Resident) -> Resident | None:
    """The nearest free resident within reach that this one has not greeted lately."""
    zone = world.zones[resident.zone]
    reach = GREET_REACH_CELLS * zone.width_pixels // zone.width_cells * 1000
    candidates = []
    for other in world.residents.values():
        if other is resident or other.zone != resident.zone or not _available(other):
            continue
        distance = abs(other.x_milli - resident.x_milli)
        ready = world.social_ready.get(world.pair(resident.identifier, other.identifier), 0) <= world.time_ms
        if distance <= reach and ready:
            candidates.append((distance, other.identifier))
    return world.residents[min(candidates)[1]] if candidates else None


def start_greet(world: World, resident: Resident) -> bool:
    """Walk over to a nearby free resident to say hello."""
    partner = _greet_partner(world, resident)
    if partner is None:
        return False
    world.social_ready[world.pair(resident.identifier, partner.identifier)] = world.time_ms + GREET_COOLDOWN_MS
    side = 1 if resident.x_milli < partner.x_milli else -1
    start(world, resident, "greet", "lonely", duration=GREET_MS)
    resident.activity.target_x = max(0, partner.x_milli - side * 24000)
    resident.activity.partner = partner.identifier
    return True


def greet_arrived(world: World, resident: Resident) -> None:
    """The greeted resident turns to answer if it is free; busy ones simply carry on."""
    partner = world.residents.get(resident.activity.partner)
    if partner is not None and _available(partner):
        partner.activity = None
        start(world, partner, "greet", "greeted", duration=GREET_MS)
        partner.activity.phase = "using"
        partner.facing = 1 if resident.x_milli > partner.x_milli else -1


def greet_completed(world: World, resident: Resident, partner_id: str) -> None:
    partner = world.residents.get(partner_id)
    if partner is None:
        return
    for member in (resident, partner):
        member.needs["social"] = min(100, member.needs["social"] + 15)
    world.adjust_relation(resident.identifier, partner_id, 2)
    world.emit("greeted", resident=resident.identifier, partner=partner_id)


def squabble(world: World, resident: Resident, activity: str) -> None:
    """Wanting the same seat as someone else costs a little mood and friendship, rarely."""
    for piece, definition in world.in_zone(resident.zone):
        if definition.activity != activity:
            continue
        for user in piece.users.values():
            key = "squabble:" + world.pair(resident.identifier, user)
            if user == resident.identifier or world.social_ready.get(key, 0) > world.time_ms:
                continue
            world.social_ready[key] = world.time_ms + SQUABBLE_COOLDOWN_MS
            world.adjust_relation(resident.identifier, user, -1)
            resident.needs["mood"] = max(0, resident.needs["mood"] - 2)
            world.emit("squabble", resident=resident.identifier, partner=user)
            return


def shared_completed(world: World, resident: Resident, piece_id: str | None) -> None:
    """Finishing a meal or a game next to someone makes them a little closer."""
    piece = world.furniture.get(piece_id) if piece_id else None
    if piece is None:
        return
    for user in piece.users.values():
        key = "shared:" + world.pair(resident.identifier, user)
        if user == resident.identifier or world.social_ready.get(key, 0) > world.time_ms:
            continue
        world.social_ready[key] = world.time_ms + SHARED_COOLDOWN_MS
        world.adjust_relation(resident.identifier, user, 1)
        world.emit("shared", resident=resident.identifier, partner=user)


def together(world: World, resident: Resident) -> int:
    """How many others are using the same piece of furniture for the same thing right now."""
    activity = resident.activity
    if activity is None or activity.furniture is None or activity.phase != "using":
        return 0
    piece = world.furniture.get(activity.furniture)
    if piece is None:
        return 0
    return sum(1 for user in piece.users.values() if user != resident.identifier
               and world.residents[user].activity is not None
               and world.residents[user].activity.phase == "using")

