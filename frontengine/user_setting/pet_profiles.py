"""Independent sprite pet identities and bounded portable local state."""
from __future__ import annotations

import copy
import json
import re
import uuid
from pathlib import Path
from typing import Callable

from frontengine.utils.json.json_repository import JsonRepository

MAX_PROFILES = 256
MAX_BYTES = 256 * 1024
_ID = re.compile(r"[0-9a-f]{32}")
_FIELDS = {"id", "name", "mood", "fullness", "affection"}


def checked_profile(record: dict) -> dict:
    """Reject unknown identity formats, control characters and out-of-range stats."""
    if not isinstance(record, dict) or set(record) != _FIELDS:
        raise ValueError("Invalid pet profile fields")
    identifier, name = record["id"], record["name"]
    if not isinstance(identifier, str) or not _ID.fullmatch(identifier):
        raise ValueError("Invalid pet identity")
    if (not isinstance(name, str) or not 1 <= len(name.strip()) <= 64
            or any(ord(char) < 32 for char in name)):
        raise ValueError("Pet name must contain 1–64 characters")
    for key, maximum in (("mood", 100), ("fullness", 100), ("affection", 1000000)):
        if type(record[key]) is not int or not 0 <= record[key] <= maximum:
            raise ValueError(f"Invalid pet {key}")
    return {**record, "name": name.strip()}


class PetProfiles:
    """Commit shared settings atomically without overwriting other pet records."""

    def __init__(self, settings: dict, save: Callable[[], object]) -> None:
        self.settings, self.save = settings, save

    def _read(self) -> dict:
        data = self.settings.get("pet_profiles")
        if data is None:
            return {"version": 1, "migrated": False, "records": {}}
        if (not isinstance(data, dict) or type(data.get("version")) is not int
                or data["version"] != 1 or type(data.get("migrated")) is not bool
                or not isinstance(data.get("records"), dict) or len(data["records"]) > MAX_PROFILES):
            raise ValueError("Invalid saved pet profiles")
        records = {}
        for identifier, record in data["records"].items():
            checked = checked_profile(record)
            if identifier != checked["id"]:
                raise ValueError("Pet identity does not match its storage key")
            records[identifier] = checked
        return {**data, "records": records}

    def profiles(self) -> list[dict]:
        """Return detached records sorted by name and stable identity."""
        return sorted(self._read()["records"].values(), key=lambda record: (record["name"], record["id"]))

    def get(self, identifier: str) -> dict:
        """Load a stable identity or fail explicitly; never silently reuse another."""
        return copy.deepcopy(self._read()["records"][identifier])

    def _commit(self, data: dict) -> None:
        if len(json.dumps(data, allow_nan=False).encode("utf-8")) > MAX_BYTES:
            raise ValueError("Pet profiles exceed the storage limit")
        old = self.settings.get("pet_profiles")
        self.settings["pet_profiles"] = data
        try:
            self.save()
        except (OSError, ValueError):
            if old is None:
                self.settings.pop("pet_profiles", None)
            else:
                self.settings["pet_profiles"] = old
            raise

    def create(self, name: str = "", source: dict | None = None) -> dict:
        """Migrate legacy shared stats once; every later pet gets fresh defaults."""
        data = self._read()
        if len(data["records"]) >= MAX_PROFILES:
            raise ValueError("At most 256 pet profiles can be saved")
        record = {"id": uuid.uuid4().hex, "name": name.strip() or f"Pet {len(data['records']) + 1}",
                  "mood": 60, "fullness": 70, "affection": 0}
        if source is not None:
            validated = checked_profile(source)
            record.update({key: validated[key] for key in ("name", "mood", "fullness", "affection")})
        elif not data["migrated"]:
            for key, legacy in (("mood", "pet_mood"), ("fullness", "pet_hunger"), ("affection", "pet_affection")):
                value = self.settings.get(legacy, record[key])
                if type(value) is int:
                    record[key] = max(0, min(1000000 if key == "affection" else 100, value))
        record = checked_profile(record)
        data["records"][record["id"]] = record
        data["migrated"] = True
        self._commit(data)
        return copy.deepcopy(record)

    def update(self, identifier: str, changes: dict) -> dict:
        """Save only this identity's stats; failed persistence restores settings."""
        if not isinstance(changes, dict) or set(changes) - (_FIELDS - {"id"}):
            raise ValueError("Invalid pet profile changes")
        data = self._read()
        record = checked_profile({**data["records"][identifier], **changes})
        data["records"][identifier] = record
        self._commit(data)
        return copy.deepcopy(record)

    def export_profile(self, identifier: str, destination: Path) -> None:
        """Atomically export this pet only, without sprites or other settings."""
        JsonRepository(destination).save({"format": "frontengine.pet-save", "version": 1,
                                          "profile": self.get(identifier)})

    def import_profile(self, source: Path) -> dict:
        """Import as a new identity so an existing/live pet can never be overwritten."""
        with source.open("rb") as file:
            raw = file.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("Pet save exceeds the size limit")
        try:
            data = json.loads(raw.decode("utf-8"))
        except RecursionError as error:
            raise ValueError("Pet save is nested too deeply") from error
        if (not isinstance(data, dict) or data.get("format") != "frontengine.pet-save"
                or type(data.get("version")) is not int or data["version"] != 1):
            raise ValueError("Unsupported pet save format")
        return self.create(source=checked_profile(data.get("profile")))
