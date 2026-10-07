"""Account-scoped publication snapshots and durable recovery records."""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path

from frontengine.utils.steam.steam_runtime import APP_ID
from frontengine.utils.workshop.workshop_manifest import checked_tree, safe_path
from frontengine.utils.workshop.workshop_package import create_snapshot, validate_content

STATES = {"prepared", "creating", "verifying", "uploading", "completed",
          "awaiting_terms", "failed", "outcome_unknown"}
PENDING = {"creating", "verifying", "uploading"}


def validate_metadata(description: str, tags: list[str], visibility: int) -> None:
    if type(visibility) is not int or visibility not in (0, 1, 2, 3):
        raise ValueError("Invalid Workshop visibility")
    if not isinstance(description, str) or "\0" in description or len(description.encode("utf-8")) >= 8000:
        raise ValueError("Description must be shorter than 8000 UTF-8 bytes")
    if not isinstance(tags, list) or len(tags) > 32 or any(
            not isinstance(t, str) or not t.strip() or "\0" in t or len(t.encode("utf-8")) > 64 for t in tags):
        raise ValueError("Tags must be nonempty and at most 64 UTF-8 bytes")


def item_id(value: str | int) -> int:
    """Accept only decimal published IDs, never floats or booleans."""
    if isinstance(value, bool) or not str(value).isascii() or not str(value).isdigit():
        raise ValueError("Published ID must be a decimal integer")
    result = int(value)
    if not 0 < result < (1 << 64) - 1:
        raise ValueError("Published ID is outside the Steam range")
    return result


def fingerprints(root: Path) -> dict[str, str]:
    result = {}
    for path in checked_tree(root):
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        result[path.relative_to(root).as_posix()] = digest.hexdigest()
    return result


class PublicationStore:
    """Persist IDs before further network calls; source presets never carry authority."""

    def __init__(self, user_id: int, root: Path | None = None) -> None:
        self.user_id = item_id(user_id)
        base = root if root is not None else Path.home() / ".frontengine" / "workshop"
        self.root = base.absolute() / str(APP_ID) / str(self.user_id) / "publications"
        # Reject junctions in any existing parent before reading or writing records.
        for parent in (self.root, *self.root.parents):
            if parent.is_symlink() or (parent.exists() and getattr(parent.lstat(), "st_file_attributes", 0) & 0x400):
                raise ValueError("Workshop storage cannot use links or junctions")
        self.root.mkdir(parents=True, exist_ok=True)

    def directory(self, operation: str) -> Path:
        if not isinstance(operation, str) or len(operation) != 32:
            raise ValueError("Invalid publication operation")
        try:
            if uuid.UUID(hex=operation).hex != operation:
                raise ValueError("Invalid publication operation")
        except (ValueError, AttributeError) as error:
            raise ValueError("Invalid publication operation") from error
        return safe_path(self.root, operation)

    def prepare(self, kind: str, source: Path, title: str, preview: Path,
                description: str = "", tags: list[str] | None = None,
                visibility: int = 2, published_id: str = "") -> dict:
        """Perform local validation/copying in a worker before any remote mutation."""
        tags = list(tags or [])
        validate_metadata(description, tags, visibility)
        published_id = str(item_id(published_id)) if published_id else ""
        operation = uuid.uuid4().hex
        directory = self.directory(operation)
        directory.mkdir()
        manifest = create_snapshot(kind, source, title, preview, directory / "snapshot")
        record = {"version": 1, "operation": operation, "app_id": APP_ID,
                  "user_id": str(self.user_id), "published_id": published_id,
                  "state": "prepared", "error": "", "manifest": manifest,
                  "description": description, "tags": tags, "visibility": visibility,
                  "fingerprints": fingerprints(directory / "snapshot")}
        self.save(record)
        return record

    def save(self, record: dict) -> None:
        directory = self.directory(record["operation"])
        target = safe_path(directory, "publication.json")
        temporary = safe_path(directory, "publication.tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(record, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)

    def load(self, operation: str, verify_snapshot: bool = True) -> dict:
        directory = self.directory(operation)
        path = safe_path(directory, "publication.json")
        if path.stat().st_size > 2 * 1024 * 1024:
            raise ValueError("Publication record exceeds its size limit")
        record = json.loads(path.read_text(encoding="utf-8"))
        if (not isinstance(record, dict) or record.get("version") != 1 or
                record.get("operation") != operation or record.get("app_id") != APP_ID or
                record.get("user_id") != str(self.user_id) or record.get("state") not in STATES):
            raise ValueError("Publication record does not belong to this Steam account")
        if record.get("published_id"):
            item_id(record["published_id"])
        validate_metadata(record.get("description"), record.get("tags"), record.get("visibility"))
        if verify_snapshot:
            snapshot = safe_path(directory, "snapshot")
            if validate_content(snapshot) != record.get("manifest") or fingerprints(snapshot) != record.get("fingerprints"):
                raise ValueError("Publication snapshot has changed; prepare a new operation")
        return record

    def records(self, recover: bool = False) -> list[dict]:
        records = []
        for directory in self.root.iterdir():
            try:
                record = self.load(directory.name, verify_snapshot=False)
                if recover and record["state"] in PENDING:
                    record.update(state="outcome_unknown", error="Steam operation was interrupted")
                    self.save(record)
                records.append(record)
            except (OSError, ValueError, KeyError):
                continue
        return records
