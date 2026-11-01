"""Words for what a resident is doing, shared by the overview card and the desktop card."""
from __future__ import annotations

from typing import TYPE_CHECKING

from frontengine.utils.multi_language.retranslate import translate
from frontengine.utils.pet_game.resident import Resident

if TYPE_CHECKING:
    from frontengine.utils.pet_game.world import World

NEED_KEYS = (("energy", "pet_home_energy", "Energy"), ("fullness", "pet_home_fullness", "Fullness"),
             ("mood", "pet_home_mood", "Mood"), ("comfort", "pet_home_comfort", "Comfort"),
             ("social", "pet_home_social", "Company"))
FRIENDS_SHOWN = 3


def result_text(code: str) -> str:
    return translate("pet_home_result_" + code, code)


def activity_text(resident: Resident, world: World | None = None) -> str:
    """Current activity with its reason and time left, plus why the last command was declined."""
    if resident.away:
        text = result_text("active_elsewhere")
    elif resident.parked:
        text = result_text("parked")
    else:
        activity = resident.activity
        kind = activity.kind if activity is not None else "idle"
        text = translate("pet_home_activity_" + kind, kind)
        if activity is not None and activity.reason:
            reason = translate("pet_home_reason_" + activity.reason, activity.reason)
            text = translate("pet_home_activity_line", "{activity} ({reason})").format(
                activity=text, reason=reason)
        left = time_left_ms(world, resident) if world is not None else None
        if left:
            text += " · " + translate("pet_home_time_left", "about {minutes} min left").format(
                minutes=max(1, round(left / 60000)))
    if resident.last_refusal:
        text += "\n" + translate("pet_home_refused", "Declined: {reason}").format(
            reason=result_text(resident.last_refusal))
    return text


def time_left_ms(world: World, resident: Resident) -> int | None:
    """Real milliseconds until a timed activity or the current unit of work ends, when known."""
    activity = resident.activity
    if activity is None:
        return None
    if activity.kind == "work" and activity.task in world.tasks:
        task = world.tasks[activity.task]
        return world.catalog.recipes[task.recipe].duration_ms - task.progress_ms
    if activity.until_ms is not None:
        return max(0, activity.until_ms - world.time_ms)
    return None


def traits_text(resident: Resident) -> str:
    names = ", ".join(translate("pet_game_trait_" + trait, trait) for trait in resident.traits)
    return translate("pet_home_traits", "Personality: {traits}").format(traits=names or "—")


def friends_text(world: World, resident: Resident) -> str:
    """Closest companions first; the line is empty for a pet living alone."""
    scores = []
    for other in world.residents.values():
        if other is not resident:
            scores.append((-world.relation(resident.identifier, other.identifier), other.name))
    if not scores:
        return ""
    parts = [f"{name} ({-score:+d})" for score, name in sorted(scores)[:FRIENDS_SHOWN]]
    return translate("pet_home_friends", "Friends: {names}").format(names=", ".join(parts))


def card_text(resident: Resident, world: World | None = None) -> str:
    needs = " · ".join(f"{translate(key, fallback)} {resident.needs[need]}" for need, key, fallback in NEED_KEYS)
    lines = [resident.name, activity_text(resident, world), needs, traits_text(resident)]
    if world is not None:
        lines.append(friends_text(world, resident))
    return "\n".join(line for line in lines if line)
