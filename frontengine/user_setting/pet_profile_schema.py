"""Versioned, detached pet identity values without asset filesystem access."""
from __future__ import annotations

import copy
import re
from frontengine.utils.pet_pack.palette import checked_colors
from frontengine.utils.pet_pack.variants import checked_variants
from frontengine.utils.pet_companion.stats import MAX_AFFECTION, TREAT_KINDS

LEGACY_FIELDS = {"id", "name", "mood", "fullness", "affection"}
PROFILE_FIELDS = LEGACY_FIELDS | {"energy", "mode", "appearance", "preferences"}
SLOTS = ("head", "neck", "body", "back")
_IDENTITY = re.compile(r"[0-9a-f]{32}")
_REFERENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")


def profile_defaults() -> dict:
    """Return independent defaults for fields introduced in version 2."""
    return {"energy": 70, "mode": "play",
            "appearance": {"character": None, "equipped": dict.fromkeys(SLOTS),
                           "saved_outfits": []},
            "preferences": {"auto_rest": True, "allow_throw": True, "allow_social": True,
                            "presentation": None}}


# Proactive chatter and animation amplitude are separate from speech bubbles and
# volume. They are optional so presentations saved before them stay valid.
CHATTER_LEVELS = ("off", "rare", "normal", "often")
MOTION_LEVELS = ("calm", "normal", "lively")
_OPTIONAL_PRESENTATION = {"chatter": CHATTER_LEVELS, "motion": MOTION_LEVELS}


def presentation_defaults() -> dict:
    """Return independent presentation values for a newly customized pet."""
    return {"size": 128, "speed": 3, "behaviour": "actions", "climb": True,
            "sit_on_windows": True, "speech_bubbles": True, "volume": 100,
            "settle_typing": False, "chatter": "normal", "motion": "normal"}


def _presentation(value: object) -> None:
    if value is None:
        return
    required = set(presentation_defaults()) - set(_OPTIONAL_PRESENTATION)
    present = set(value).intersection(_OPTIONAL_PRESENTATION) if isinstance(value, dict) else set()
    _fields(value, required | present, "pet presentation")
    for key in present:
        if value[key] not in _OPTIONAL_PRESENTATION[key]:
            raise ValueError(f"Invalid pet {key}")
    for key, bounds in {"size": (16, 512), "speed": (1, 20), "volume": (0, 100)}.items():
        if type(value[key]) is not int or not bounds[0] <= value[key] <= bounds[1]:
            raise ValueError(f"Invalid pet {key}")
    if value["behaviour"] not in ("actions", "floor", "wander", "chase"):
        raise ValueError("Invalid pet behaviour")
    for key in ("climb", "sit_on_windows", "speech_bubbles", "settle_typing"):
        if type(value[key]) is not bool:
            raise ValueError(f"Invalid pet {key}")


def _fields(value: object, keys: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"Invalid {label} fields")


def _name(value: object) -> None:
    if (not isinstance(value, str) or not 1 <= len(value.strip()) <= 64
            or len(value) > 64 or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise ValueError("Pet name must contain 1–64 characters")


def _reference_string(value: object) -> None:
    if not isinstance(value, str) or not _REFERENCE.fullmatch(value):
        raise ValueError("Invalid asset or outfit reference")


def _asset(value: object) -> None:
    if value is None:
        return
    _fields(value, {"id", "version"}, "asset reference")
    _reference_string(value["id"])
    _reference_string(value["version"])


def _equipped(value: object) -> None:
    _fields(value, set(SLOTS), "equipped outfit")
    for asset in value.values():
        _asset(asset)


def _appearance(value: object) -> None:
    _fields(value, {"character", "equipped", "saved_outfits"}
            | (set(value).intersection({'colors', 'variants'}) if isinstance(value, dict) else set()), "appearance")
    checked_colors(value.get('colors', {}))
    checked_variants(value.get('variants', {}))
    _asset(value["character"])
    _equipped(value["equipped"])
    outfits = value["saved_outfits"]
    if not isinstance(outfits, list) or len(outfits) > 20:
        raise ValueError("At most 20 outfits can be saved")
    identifiers = set()
    for outfit in outfits:
        _fields(outfit, {"id", "name", "equipped"}
                | (set(outfit).intersection({'colors', 'variants', 'character'}) if isinstance(outfit, dict) else set()), "saved outfit")
        checked_colors(outfit.get('colors', {}))
        checked_variants(outfit.get('variants', {}))
        if 'character' in outfit:
            _asset(outfit['character'])
        _reference_string(outfit["id"])
        if outfit["id"] in identifiers:
            raise ValueError("Duplicate saved outfit identity")
        identifiers.add(outfit["id"])
        _name(outfit["name"])
        _equipped(outfit["equipped"])


def checked_profile(record: dict, version: int | None = None) -> dict:
    """Validate an exact schema and normalize legacy identities without writes."""
    if version is None:
        version = 1 if isinstance(record, dict) and set(record) == LEGACY_FIELDS else 2
    if type(version) is not int or version not in (1, 2):
        raise ValueError("Unsupported pet profile version")
    _fields(record, LEGACY_FIELDS if version == 1 else PROFILE_FIELDS, "pet profile")
    if not isinstance(record["id"], str) or not _IDENTITY.fullmatch(record["id"]):
        raise ValueError("Invalid pet identity")
    _name(record["name"])
    limits = {"mood": 100, "fullness": 100, "affection": MAX_AFFECTION}
    if version == 2:
        limits["energy"] = 100
    for key, maximum in limits.items():
        if type(record[key]) is not int or not 0 <= record[key] <= maximum:
            raise ValueError(f"Invalid pet {key}")
    if version == 1:
        return {**copy.deepcopy(record), **profile_defaults()}
    if not isinstance(record["mode"], str) or record["mode"] not in ("play", "work", "rest"):
        raise ValueError("Invalid pet mode")
    _appearance(record["appearance"])
    preferences = record["preferences"]
    required = {"auto_rest", "allow_throw", "allow_social"}
    if (not isinstance(preferences, dict) or not required <= set(preferences)
            or set(preferences) - required - {'presentation', 'taste'}):
        raise ValueError("Invalid preferences fields")
    if any(type(preferences[key]) is not bool for key in required):
        raise ValueError("Pet preferences must be booleans")
    _presentation(preferences.get("presentation"))
    if 'taste' in preferences:
        taste = preferences['taste']
        _fields(taste, {'favorite', 'disliked'}, 'pet taste')
        if any(value is not None and (not isinstance(value, str) or value not in TREAT_KINDS)
               for value in taste.values()):
            raise ValueError('Invalid pet taste choice')
        if taste['favorite'] is not None and taste['favorite'] == taste['disliked']:
            raise ValueError('Favorite and disliked treats must differ')
    normalized = copy.deepcopy(record)
    normalized["preferences"].setdefault("presentation", None)
    return normalized
