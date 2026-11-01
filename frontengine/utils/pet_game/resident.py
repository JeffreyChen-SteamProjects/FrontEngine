"""Residents: a pet identity living in the home, with needs, skills and a routine.

A resident keeps the same UUID as its saved pet profile. Care values start from
that profile and, while the home owns the pet, the world is their only writer.
The current activity is runtime state: after a restart residents start idle
and paused work resumes from its saved progress.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from frontengine.utils.pet_companion.stats import MAX_AFFECTION
from frontengine.utils.pet_game.catalog import NEEDS, PROFESSIONS
from frontengine.utils.pet_game.layout import RESIDENT_ID, MAX_ZONE_CELLS, check_local_id, checked_int
from frontengine.utils.pet_game.schedule import TEMPLATES

TRAITS = ("diligent", "playful", "quiet", "social")
MAX_TRAITS = 2
MAX_EXPERIENCE = 10_000_000
LEVEL_STEPS = (0, 40, 120, 300, 700, 1500)


def skill_level(experience: int) -> int:
    return sum(1 for threshold in LEVEL_STEPS if experience >= threshold)


@dataclass
class Activity:
    """What a resident is doing now. Never persisted."""

    kind: str                       # sleep/eat/work/play/relax/wander/idle/wait/drag/nap/snack
    reason: str
    furniture: str | None = None
    point: int | None = None
    task: str | None = None
    phase: str = "moving"           # moving / using
    target_x: int = 0               # milli-pixels
    until_ms: int | None = None     # end of a timed activity
    started_ms: int = 0


@dataclass
class Resident:
    identifier: str
    name: str
    zone: str
    x_milli: int
    needs: dict[str, int]
    affection: int = 0
    skills: dict[str, int] = field(default_factory=dict)
    traits: tuple[str, ...] = ()
    routine: str = "standard"
    parked: bool = False
    away: bool = False              # runtime: identity is live elsewhere, not simulated
    facing: int = 1
    activity: Activity | None = None
    accumulators: dict[str, int] = field(default_factory=dict)
    commands: list[str] = field(default_factory=list)
    decide_after_ms: int = 0
    last_refusal: str | None = None

    def level(self, profession: str) -> int:
        return skill_level(self.skills.get(profession, 0))

    def to_dict(self) -> dict:
        return {"id": self.identifier, "name": self.name, "zone": self.zone, "x": self.x_milli,
                "needs": dict(self.needs), "affection": self.affection,
                "skills": dict(sorted(self.skills.items())), "traits": list(self.traits),
                "routine": self.routine, "parked": self.parked}

    @classmethod
    def from_dict(cls, data: object) -> Resident:
        keys = {"id", "name", "zone", "x", "needs", "affection", "skills", "traits", "routine", "parked"}
        if not isinstance(data, dict) or set(data) != keys:
            raise ValueError("Invalid resident fields")
        if not isinstance(data["id"], str) or not RESIDENT_ID.fullmatch(data["id"]):
            raise ValueError("Invalid resident identity")
        return cls(data["id"], _checked_name(data["name"]), check_local_id(data["zone"], "z"),
                   _bounded(data["x"], 0, MAX_ZONE_CELLS * 32 * 1000, "resident position"),
                   _checked_needs(data["needs"]),
                   _bounded(data["affection"], 0, MAX_AFFECTION, "affection"),
                   _checked_skills(data["skills"]), _checked_traits(data["traits"]),
                   _checked_routine(data["routine"]), _checked_bool(data["parked"]))


_bounded = checked_int


def _checked_bool(value: object) -> bool:
    if type(value) is not bool:
        raise ValueError("Expected a boolean")
    return value


def _checked_name(value: object) -> str:
    if (not isinstance(value, str) or not 1 <= len(value.strip()) <= 64 or len(value) > 64
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise ValueError("Invalid resident name")
    return value


def _checked_needs(value: object) -> dict[str, int]:
    if not isinstance(value, dict) or set(value) != set(NEEDS):
        raise ValueError("Invalid resident needs")
    return {need: _bounded(value[need], 0, 100, need) for need in NEEDS}


def _checked_skills(value: object) -> dict[str, int]:
    if not isinstance(value, dict) or set(value) - set(PROFESSIONS):
        raise ValueError("Invalid resident skills")
    return {key: _bounded(amount, 0, MAX_EXPERIENCE, "experience") for key, amount in value.items()}


def _checked_traits(value: object) -> tuple[str, ...]:
    if (not isinstance(value, list) or len(value) > MAX_TRAITS or len(set(value)) != len(value)
            or any(trait not in TRAITS for trait in value)):
        raise ValueError("Invalid resident traits")
    return tuple(value)


def _checked_routine(value: object) -> str:
    if value not in TEMPLATES:
        raise ValueError("Unknown resident routine")
    return value


def resident_from_profile(profile: dict, zone: str, x_milli: int) -> Resident:
    """Adopt a validated pet profile; care values carry over, nothing is reset."""
    return Resident(profile["id"], profile["name"], zone, x_milli,
                    {"energy": profile.get("energy", 70), "fullness": profile["fullness"],
                     "mood": profile["mood"]}, affection=profile["affection"])
