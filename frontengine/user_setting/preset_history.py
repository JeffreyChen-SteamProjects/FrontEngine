"""Bounded immutable preset settings snapshots, separate from media packages."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from frontengine.utils.json.json_repository import JsonRepository
from frontengine.utils.logging.loggin_instance import front_engine_logger

MAX_BYTES = 1024 * 1024
MAX_SNAPSHOT_BYTES = 8 * MAX_BYTES
MAX_VERSIONS = 50
_IDENTIFIER = re.compile(r"[0-9a-f]{64}")


def checked_state(data: dict) -> tuple[dict, str]:
    """Return a detached finite JSON object and its content identifier."""
    if not isinstance(data, dict):
        raise ValueError("Preset settings must be a JSON object")
    try:
        raw = json.dumps(data, ensure_ascii=False, sort_keys=True, allow_nan=False)
        if len(raw.encode("utf-8")) > MAX_BYTES:
            raise ValueError("Preset settings exceed 1 MiB")
        detached = json.loads(raw)
    except (TypeError, RecursionError) as error:
        raise ValueError("Preset settings cannot be serialized") from error
    pending = [(detached, 0)]
    count = 0
    while pending:
        value, depth = pending.pop()
        count += 1
        if count > 20000 or depth > 32:
            raise ValueError("Preset settings exceed structural limits")
        children = value.values() if isinstance(value, dict) else value if isinstance(value, list) else ()
        pending.extend((child, depth + 1) for child in children)
    return detached, hashlib.sha256(raw.encode("utf-8")).hexdigest()


class PresetHistory:
    """Keep up to 50 distinct configurations for one sanitized preset name."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def snapshot(self, data: dict) -> tuple[str, bool]:
        """Write before replacing a preset; return ID and whether it was new."""
        state, identifier = checked_state(data)
        path = self.directory / (identifier + ".json")
        if path.exists():
            # A damaged snapshot must never silently masquerade as a backup.
            self.load(identifier)
            return identifier, False
        self.directory.mkdir(parents=True, exist_ok=True)
        record = {"format": "frontengine.preset-history", "version": 1,
                  "created": datetime.now(timezone.utc).isoformat(), "state": state}
        if len(json.dumps(record, indent=4).encode("utf-8")) > MAX_SNAPSHOT_BYTES:
            raise ValueError("Preset snapshot exceeds the size limit")
        JsonRepository(path).save(record)
        return identifier, True

    def load(self, identifier: str) -> dict:
        """Validate bounded snapshot input and its digest before applying it."""
        return self._record(identifier)["state"]

    def _record(self, identifier: str) -> dict:
        if not isinstance(identifier, str) or not _IDENTIFIER.fullmatch(identifier):
            raise ValueError("Invalid preset version identifier")
        path = self.directory / (identifier + ".json")
        with path.open("rb") as source:
            raw = source.read(MAX_SNAPSHOT_BYTES + 1)
        if len(raw) > MAX_SNAPSHOT_BYTES:
            raise ValueError("Preset snapshot exceeds the size limit")
        try:
            record = json.loads(raw.decode("utf-8"))
        except RecursionError as error:
            raise ValueError("Preset snapshot is nested too deeply") from error
        if (not isinstance(record, dict) or record.get("format") != "frontengine.preset-history"
                or type(record.get("version")) is not int or record["version"] != 1):
            raise ValueError("Unsupported preset snapshot")
        state, digest = checked_state(record.get("state"))
        if digest != identifier:
            raise ValueError("Preset snapshot content has changed")
        created = record.get("created")
        if not isinstance(created, str) or datetime.fromisoformat(created).tzinfo is None:
            raise ValueError("Preset snapshot has no timezone-aware timestamp")
        record["state"] = state
        return record

    def versions(self) -> list[tuple[str, str]]:
        """List valid IDs and UTC timestamps, newest first; damaged files fail."""
        rows = []
        for path in self.directory.glob("*.json"):
            record = self._record(path.stem)
            rows.append((path.stem, record["created"]))
        return sorted(rows, key=lambda row: row[1], reverse=True)

    def discard(self, identifier: str) -> None:
        """Remove only a newly created snapshot when the active save fails."""
        if not _IDENTIFIER.fullmatch(identifier):
            raise ValueError("Invalid preset version identifier")
        (self.directory / (identifier + ".json")).unlink(missing_ok=True)

    def prune(self) -> None:
        """Retention cleanup cannot turn an already committed save into failure."""
        try:
            for identifier, _created in self.versions()[MAX_VERSIONS:]:
                self.discard(identifier)
        except (OSError, ValueError) as error:
            front_engine_logger.warning(f"[PresetHistory] retention failed: {error!r}")


def compare_states(before: dict, after: dict) -> str:
    """Show deterministic JSON field changes, without modifying either state."""
    lines = []
    missing = object()
    pending = [("", before, after)]
    while pending:
        path, old, new = pending.pop()
        if isinstance(old, dict) and isinstance(new, dict):
            for key in sorted(old.keys() | new.keys(), reverse=True):
                escaped = key.replace("~", "~0").replace("/", "~1")
                pending.append((path + "/" + escaped, old.get(key, missing), new.get(key, missing)))
        elif old != new:
            render = lambda value: "∅" if value is missing else json.dumps(value, ensure_ascii=False)
            lines.append(f"{path}: {render(old)} → {render(new)}")
    return "\n".join(lines)
