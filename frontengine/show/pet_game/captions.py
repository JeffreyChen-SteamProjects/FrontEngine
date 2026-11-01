"""Words for what a resident is doing, shared by the overview card and the desktop card."""
from __future__ import annotations

from frontengine.utils.multi_language.retranslate import translate
from frontengine.utils.pet_game.resident import Resident

NEED_KEYS = (("energy", "pet_home_energy", "Energy"), ("fullness", "pet_home_fullness", "Fullness"),
             ("mood", "pet_home_mood", "Mood"))


def result_text(code: str) -> str:
    return translate("pet_home_result_" + code, code)


def activity_text(resident: Resident) -> str:
    """Current activity with its reason, plus why the last command was declined."""
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
    if resident.last_refusal:
        text += "\n" + translate("pet_home_refused", "Declined: {reason}").format(
            reason=result_text(resident.last_refusal))
    return text


def card_text(resident: Resident) -> str:
    needs = " · ".join(f"{translate(key, fallback)} {resident.needs[need]}" for need, key, fallback in NEED_KEYS)
    return f"{resident.name}\n{activity_text(resident)}\n{needs}"
