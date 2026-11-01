"""Growth: tutorial goals, daily commissions, residents' wishes, life events and the celebration.

Everything here is derived from world state and counters, checked every 30 s
of world time, and seeded from the home identity rather than the simulation's
random stream, so looking at goals never changes what happens in the home.
Rewards are paid once through the ledger with goal-specific transaction IDs.
Nothing expires: there are no streaks, timers or missed-day penalties.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

from frontengine.utils.pet_companion.stats import MAX_AFFECTION
from frontengine.utils.pet_game.environment import sky, weather
from frontengine.utils.pet_game.layout import RESIDENT_ID, checked_int
from frontengine.utils.pet_game.schedule import DAY_MS, game_day

if TYPE_CHECKING:
    from frontengine.utils.pet_game.world import World

CHECK_MS = 30000
MAX_STATS = 256
MAX_EVENTS = 50
WISH_COOLDOWN_MS = 5 * 60 * 1000
BIRTHDAY_EVERY_DAYS = 7
CELEBRATION_COINS = 100
WISH_MOOD, WISH_AFFECTION = 10, 3


@dataclass(frozen=True)
class Goal:
    identifier: str
    measure: Callable[[World], tuple[int, int]]     # (current, target)
    coins: int


def _stat(world: World, *keys: str) -> int:
    return sum(world.progress.stats.get(key, 0) for key in keys)


def placed(world: World, category: str) -> int:
    return sum(1 for piece in world.furniture.values() if world.definition(piece).category == category)


def goal_done(world: World, goal: Goal) -> bool:
    current, target = goal.measure(world)
    return current >= target


TUTORIAL = (
    Goal("move_in", lambda w: (len(w.residents), 1), 5),
    Goal("place_bed", lambda w: (placed(w, "bed"), 1), 5),
    Goal("place_table", lambda w: (placed(w, "table"), 1), 5),
    Goal("first_care", lambda w: (_stat(w, "completed:eat", "completed:snack", "completed:sleep",
                                        "completed:nap"), 1), 5),
    Goal("place_station", lambda w: (placed(w, "workstation"), 1), 5),
    Goal("first_work", lambda w: (_stat(w, "settled"), 1), 10),
    Goal("buy_furniture", lambda w: (_stat(w, "bought"), 1), 10),
    Goal("decorate", lambda w: (placed(w, "decoration"), 1), 5),
    Goal("second_resident", lambda w: (len(w.residents), 2), 10),
    Goal("shared_moment", lambda w: (_stat(w, "greeted", "shared"), 1), 15),
)
# Milestones raise the home level; they are reached by living, not by waiting.
MILESTONES = (
    lambda w: all(goal_done(w, goal) for goal in TUTORIAL),
    lambda w: _stat(w, "settled:letter", "settled:story") > 0,
    lambda w: _stat(w, "settled:herbs", "settled:flowers") > 0,
    lambda w: _stat(w, "settled:toy", "settled:stool") > 0,
    lambda w: len(w.residents) >= 3,
    lambda w: len(w.furniture) >= 10,
    lambda w: any(value >= 20 for value in w.relations.values()),
    lambda w: w.progress.goals.get("celebration") == "claimed",
)
COMMISSIONS = (("herb", 3, 18), ("herb", 5, 30), ("flower", 2, 24), ("toy", 1, 40), ("toy", 2, 85),
               ("furniture:stool", 1, 70))
WISHES = {
    "plant": lambda w, r: placed(w, "decoration"),
    "friend_meal": lambda w, r: _stat(w, "shared"),
    "new_leisure": lambda w, r: placed(w, "leisure"),
    "play_time": lambda w, r: _stat(w, "completed:play"),
    "cozy_bed": lambda w, r: sum(1 for p in w.furniture.values() if p.definition == "bed_cozy"),
}


MAX_STATION_LEVEL = 3


def _checked_upgrades(value: object) -> dict[str, int]:
    if not isinstance(value, dict) or len(value) > 64:
        raise ValueError("Invalid station upgrades")
    for key, level in value.items():
        if not isinstance(key, str) or not 1 <= len(key) <= 48:
            raise ValueError("Invalid station upgrade")
        checked_int(level, 2, MAX_STATION_LEVEL, "station level")
    return dict(value)


@dataclass
class Progress:
    stats: dict[str, int] = field(default_factory=dict)
    goals: dict[str, str] = field(default_factory=dict)          # goal -> claimed / skipped
    commissions: dict = field(default_factory=lambda: {"day": 0, "offers": []})
    wishes: dict[str, dict] = field(default_factory=dict)        # resident -> {wish, base, ready}
    arrivals: dict[str, int] = field(default_factory=dict)       # resident -> world time it moved in
    events: list[dict] = field(default_factory=list)
    upgrades: dict[str, int] = field(default_factory=dict)       # workstation kind -> level 2..3
    next_check_ms: int = 0                                       # runtime only

    def count(self, key: str) -> None:
        if key in self.stats or len(self.stats) < MAX_STATS:
            self.stats[key] = min(10 ** 9, self.stats.get(key, 0) + 1)

    def to_dict(self) -> dict:
        return {"stats": dict(sorted(self.stats.items())), "goals": dict(sorted(self.goals.items())),
                "commissions": {"day": self.commissions["day"], "offers": [dict(o) for o in self.commissions["offers"]]},
                "wishes": {key: dict(value) for key, value in sorted(self.wishes.items())},
                "arrivals": dict(sorted(self.arrivals.items())), "events": [dict(e) for e in self.events],
                "upgrades": dict(sorted(self.upgrades.items()))}

    @classmethod
    def from_dict(cls, data: object) -> Progress:
        keys = {"stats", "goals", "commissions", "wishes", "arrivals", "events"}
        if not isinstance(data, dict) or set(data) not in (keys, keys | {"upgrades"}):   # upgrades: version 6
            raise ValueError("Invalid home progress")
        progress = cls()
        progress.stats = _checked_counts(data["stats"], MAX_STATS)
        progress.goals = _checked_goals(data["goals"])
        progress.commissions = _checked_commissions(data["commissions"])
        progress.wishes = _checked_wishes(data["wishes"])
        progress.arrivals = {key: checked_int(value, 0, 10 ** 13, "arrival")
                             for key, value in _checked_residents(data["arrivals"]).items()}
        progress.events = _checked_events(data["events"])
        progress.upgrades = _checked_upgrades(data.get("upgrades", {}))
        return progress


# ----- validation of saved progress ------------------------------------------------------

def _checked_counts(value: object, limit: int) -> dict[str, int]:
    if not isinstance(value, dict) or len(value) > limit:
        raise ValueError("Invalid progress counters")
    for key, amount in value.items():
        if not isinstance(key, str) or not 0 < len(key) <= 64:
            raise ValueError("Invalid progress counter name")
        checked_int(amount, 0, 10 ** 9, "progress counter")
    return dict(value)


# Goals that were replaced: an old save's state carries over to the new goal, so a
# reward is never paid twice and the save still loads. "Choose a routine" went when
# routines became automatic.
RENAMED_GOALS = {"set_routine": "decorate"}


def _checked_goals(value: object) -> dict[str, str]:
    known = {goal.identifier for goal in TUTORIAL} | {"celebration"} | set(RENAMED_GOALS)
    if not isinstance(value, dict) or set(value) - known or any(
            state not in ("claimed", "skipped") for state in value.values()):
        raise ValueError("Invalid goal states")
    goals = dict(value)
    for old, new in RENAMED_GOALS.items():
        if old in goals:
            goals.setdefault(new, goals.pop(old))
    return goals


def _checked_residents(value: object) -> dict:
    if not isinstance(value, dict) or len(value) > 64 or any(
            not isinstance(key, str) or not RESIDENT_ID.fullmatch(key) for key in value):
        raise ValueError("Invalid resident progress")
    return value


def _checked_commissions(value: object) -> dict:
    if not isinstance(value, dict) or set(value) != {"day", "offers"} or not isinstance(value["offers"], list) \
            or len(value["offers"]) > 3:
        raise ValueError("Invalid commissions")
    offers = []
    for offer in value["offers"]:
        if not isinstance(offer, dict) or set(offer) != {"item", "count", "coins", "done"} \
                or (offer["item"], offer["count"], offer["coins"]) not in COMMISSIONS \
                or not isinstance(offer["done"], bool):
            raise ValueError("Invalid commission")
        offers.append(dict(offer))
    return {"day": checked_int(value["day"], 0, 10 ** 7, "commission day"), "offers": offers}


def _checked_wishes(value: object) -> dict[str, dict]:
    wishes = {}
    for key, wish in _checked_residents(value).items():
        if not isinstance(wish, dict) or set(wish) != {"wish", "base", "ready"} or \
                (wish["wish"] is not None and wish["wish"] not in WISHES):
            raise ValueError("Invalid wish")
        wishes[key] = {"wish": wish["wish"], "base": checked_int(wish["base"], 0, 10 ** 9, "wish base"),
                       "ready": checked_int(wish["ready"], 0, 10 ** 13, "wish time")}
    return wishes


def _checked_events(value: object) -> list[dict]:
    if not isinstance(value, list) or len(value) > MAX_EVENTS:
        raise ValueError("Invalid life events")
    for event in value:
        if (not isinstance(event, dict) or set(event) != {"kind", "day", "resident"}
                or event["kind"] not in LIFE_EVENTS or not isinstance(event["resident"], (str, type(None)))):
            raise ValueError("Invalid life event")
        checked_int(event["day"], 1, 10 ** 7, "event day")
    return [dict(event) for event in value]


# ----- tutorial and level ---------------------------------------------------------------

def goal_state(world: World, goal: Goal) -> str:
    saved = world.progress.goals.get(goal.identifier)
    return saved or ("done" if goal_done(world, goal) else "open")


def claim(world: World, identifier: str) -> str:
    goal = next((goal for goal in TUTORIAL if goal.identifier == identifier), None)
    if goal is None:
        return "unknown"
    if goal_state(world, goal) != "done":
        return "not_ready"
    result = world.ledger.apply("goal:" + identifier, "goal", goal.coins)
    if result in ("accepted", "duplicate"):
        world.progress.goals[identifier] = "claimed"
        world.emit("goal_claimed", goal=identifier, coins=goal.coins)
    return result


def skip_tutorial(world: World) -> str:
    """Skipping gives no rewards and hides nothing; every goal can still be reviewed."""
    for goal in TUTORIAL:
        world.progress.goals.setdefault(goal.identifier, "skipped")
    return "accepted"


def home_level(world: World) -> int:
    return 1 + sum(1 for reached in MILESTONES if reached(world))


def unlocked(world: World, level_needed: int) -> bool:
    """Free arranging has everything; a managed home opens pieces and jobs as its level rises."""
    return world.sandbox or level_needed <= 1 or home_level(world) >= level_needed


# ----- celebration (the 1.0 stage goal) ---------------------------------------------------

def celebration_ready(world: World) -> bool:
    professions = (MILESTONES[1], MILESTONES[2], MILESTONES[3])
    return (len(world.residents) >= 2 and all(reached(world) for reached in professions)
            and world.progress.goals.get("celebration") != "claimed")


def celebrate(world: World) -> str:
    """A one-time home party; free life simply continues afterwards."""
    if not celebration_ready(world):
        return "not_ready"
    result = world.ledger.apply("goal:celebration", "celebration", CELEBRATION_COINS)
    if result not in ("accepted", "duplicate"):
        return result
    world.progress.goals["celebration"] = "claimed"
    for resident in world.residents.values():
        resident.needs["mood"] = min(100, resident.needs["mood"] + 20)
        resident.needs["social"] = min(100, resident.needs["social"] + 20)
    _life_event(world, "celebration", None)
    return "accepted"


# ----- commissions ------------------------------------------------------------------------

def _seeded(world: World, *parts: object) -> int:
    text = "|".join([world.home, *map(str, parts)])
    return int.from_bytes(hashlib.sha256(text.encode("ascii")).digest()[:8], "big")


def refresh_commissions(world: World) -> None:
    """Three offers per game day; unfinished ones are simply replaced, never punished."""
    day = game_day(world.time_ms)
    if world.progress.commissions["day"] == day:
        return
    seed, pool = _seeded(world, "commissions", day), list(COMMISSIONS)
    offers = []
    for index in range(3):
        item, count, coins = pool.pop((seed >> (index * 8)) % len(pool))
        offers.append({"item": item, "count": count, "coins": coins, "done": False})
    world.progress.commissions = {"day": day, "offers": offers}


def deliver(world: World, index: int) -> str:
    offers = world.progress.commissions["offers"]
    if not 0 <= index < len(offers) or offers[index]["done"]:
        return "unknown"
    offer = offers[index]
    transaction = f"commission:{world.progress.commissions['day']}:{index}"
    result = world.ledger.apply(transaction, "commission", offer["coins"], {offer["item"]: -offer["count"]})
    if result == "insufficient":
        return "none_stored"
    if result in ("accepted", "duplicate"):
        offer["done"] = True
        world.emit("commission_done", item=offer["item"], coins=offer["coins"])
    return result


# ----- wishes -------------------------------------------------------------------------------

def _update_wish(world: World, resident) -> None:
    state = world.progress.wishes.setdefault(resident.identifier, {"wish": None, "base": 0, "ready": 0})
    wish = state["wish"]
    if wish is None:
        if world.time_ms >= state["ready"]:
            names = sorted(WISHES)
            wish = names[_seeded(world, resident.identifier, _stat(world, "wish_granted")) % len(names)]
            state.update(wish=wish, base=WISHES[wish](world, resident))
        return
    if WISHES[wish](world, resident) > state["base"]:
        resident.needs["mood"] = min(100, resident.needs["mood"] + WISH_MOOD)
        resident.affection = min(MAX_AFFECTION, resident.affection + WISH_AFFECTION)
        state.update(wish=None, base=0, ready=world.time_ms + WISH_COOLDOWN_MS)
        world.emit("wish_granted", resident=resident.identifier, wish=wish)


# ----- life events ---------------------------------------------------------------------------

LIFE_EVENTS = ("first_creation", "friends_dinner", "birthday", "celebration", "rainy_day", "starry_night",
               "new_friend", "skilled", "green_home", "full_house", "first_story", "harvest")
FRIEND_LEVEL, SKILLED_LEVEL, GREEN_HOME_DECORATIONS, FULL_HOUSE, HARVEST_UNITS = 20, 3, 5, 4, 10


def _life_event(world: World, kind: str, resident: str | None) -> None:
    world.progress.events = (world.progress.events + [
        {"kind": kind, "day": game_day(world.time_ms), "resident": resident}])[-MAX_EVENTS:]
    world.emit("life_event", event=kind, resident=resident)


def _happened(world: World, kind: str, resident: str | None = None, day: int | None = None) -> bool:
    return any(event["kind"] == kind and (resident is None or event["resident"] == resident)
               and (day is None or event["day"] == day) for event in world.progress.events)


def _once_events(world: World) -> None:
    """Home milestones that happen once in a home's life."""
    reached = {
        "first_creation": _stat(world, "settled:toy", "settled:stool") > 0,
        "first_story": _stat(world, "settled:story") > 0,
        "harvest": _stat(world, "settled:herbs", "settled:flowers") >= HARVEST_UNITS,
        "green_home": placed(world, "decoration") >= GREEN_HOME_DECORATIONS,
        "full_house": len(world.residents) >= FULL_HOUSE,
    }
    for kind, happened_now in reached.items():
        if happened_now and not _happened(world, kind):
            _life_event(world, kind, None)


def _daily_events(world: World, day: int) -> None:
    """Moments that can come back on another day: dinners and the sky."""
    awake = [r for r in world.residents.values() if not r.parked and not r.away
             and (r.activity is None or r.activity.kind not in ("sleep", "nap"))]
    eating = [r for r in awake if r.activity is not None and r.activity.kind == "eat" and r.activity.phase == "using"]
    today = {
        "friends_dinner": len(eating) >= 3,
        "rainy_day": bool(awake) and weather(world.home, world.time_ms) == "rain",
        "starry_night": bool(awake) and sky(world.time_ms) == "night"
        and weather(world.home, world.time_ms) == "clear",
    }
    for kind, happened_now in today.items():
        if happened_now and not _happened(world, kind, day=day):
            _life_event(world, kind, None)


def _resident_events(world: World) -> None:
    """A pet's first close friend and first skilled profession, once each."""
    for identifier in sorted(world.residents):
        resident = world.residents[identifier]
        friendly = any(value >= FRIEND_LEVEL for key, value in world.relations.items()
                       if identifier in key.split("|"))
        if friendly and not _happened(world, "new_friend", identifier):
            _life_event(world, "new_friend", identifier)
        skilled = any(resident.level(profession) >= SKILLED_LEVEL for profession in resident.skills)
        if skilled and not _happened(world, "skilled", identifier):
            _life_event(world, "skilled", identifier)


def _check_events(world: World) -> None:
    day = game_day(world.time_ms)
    _once_events(world)
    _daily_events(world, day)
    _resident_events(world)
    for identifier, since in world.progress.arrivals.items():
        days = (world.time_ms - since) // DAY_MS
        if days and days % BIRTHDAY_EVERY_DAYS == 0 and identifier in world.residents \
                and not _happened(world, "birthday", identifier, day):
            world.residents[identifier].needs["mood"] = min(100, world.residents[identifier].needs["mood"] + 10)
            _life_event(world, "birthday", identifier)


def _automate(world: World) -> None:
    """Rewards are taken and commissions handed in by themselves; the inbox says what happened."""
    if not world.automatic:
        return
    for goal in TUTORIAL:
        if goal_state(world, goal) == "done":
            claim(world, goal.identifier)
    for index, offer in enumerate(world.progress.commissions["offers"]):
        if not offer["done"] and world.ledger.available(offer["item"]) >= offer["count"]:
            deliver(world, index)


def update(world: World) -> None:
    """Called from the simulation step; does real work every 30 s of world time."""
    if world.time_ms < world.progress.next_check_ms:
        return
    world.progress.next_check_ms = world.time_ms + CHECK_MS
    refresh_commissions(world)
    _automate(world)
    for identifier in sorted(world.residents):
        resident = world.residents[identifier]
        if not resident.parked and not resident.away:
            _update_wish(world, resident)
    for identifier in [key for key in world.progress.wishes if key not in world.residents]:
        del world.progress.wishes[identifier]
    _check_events(world)
