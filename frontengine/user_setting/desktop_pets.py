"""Which pets were on the desktop when FrontEngine last closed, so they come back on the next start.

``pet_desktop_pets`` in the settings is a list of entries: ``{"id"}`` for a pet drawn from its
layered character (the identity says what it wears), ``{"id", "path"[, "script"]}`` for a Puppet
pet with its model and script. It is external data, so it is checked here: malformed entries,
duplicate identities, Puppet files that are gone and anything past ``MAX_RETURNING`` are dropped,
never trusted through. Entries written before pets were layered only carry the picture they were
started with; the picture is ignored and the pet comes back as its identity's character.
"""
from __future__ import annotations

import re
from pathlib import Path

from frontengine.user_setting.pet_looks import MAX_PATH

RETURN_KEY = "pet_desktop_return"
PETS_KEY = "pet_desktop_pets"
MAX_RETURNING = 16
_ID = re.compile(r"[0-9a-f]{32}")
_KEYS = {"id", "path", "script"}


def _file(value: object) -> Path | None:
    if not isinstance(value, str) or not value or len(value) > MAX_PATH:
        return None
    try:
        path = Path(value).resolve()
        return path if path.is_file() else None
    except OSError:
        return None


def _checked_puppet(identifier: str, entry: dict) -> dict | None:
    model = _file(entry["path"])
    if model is None:
        return None
    checked = {"id": identifier, "path": str(model)}
    if "script" in entry:
        script = _file(entry["script"])
        if script is None:
            return None
        checked["script"] = str(script)
    return checked


def _checked_entry(entry: object) -> dict | None:
    if not isinstance(entry, dict) or not {"id"} <= set(entry) <= _KEYS:
        return None
    identifier, path = entry["id"], entry.get("path")
    if not isinstance(identifier, str) or not _ID.fullmatch(identifier):
        return None
    if path is not None and (not isinstance(path, str) or not path or len(path) > MAX_PATH):
        return None
    if path is not None and Path(path).suffix.lower() == ".puppet":
        return _checked_puppet(identifier, entry)
    return None if "script" in entry else {"id": identifier}


def checked_returning(value: object) -> list[dict]:
    """The pets that may come back, in order, at most ``MAX_RETURNING`` and each identity once."""
    if not isinstance(value, list):
        return []
    result, seen = [], set()
    for entry in value:
        checked = _checked_entry(entry)
        if checked is None or checked["id"] in seen:
            continue
        seen.add(checked["id"])
        result.append(checked)
        if len(result) == MAX_RETURNING:
            break
    return result


def desktop_record(pets) -> list[dict]:
    """The identities of the live desktop pets, with a Puppet's model and script, for the next start."""
    record = []
    for pet in pets:
        session = getattr(pet, "profile_session", None)
        if session is None or getattr(session, "_closed", False):
            continue
        entry = {"id": session.identifier}
        path = getattr(pet, "path", None)
        if path:
            entry["path"] = str(path)
            script = getattr(pet, "script_path", None)
            if script:
                entry["script"] = str(script)
        record.append(entry)
    return checked_returning(record)
