"""Validated subscription versions isolated from Steam's mutable install folders."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

from frontengine.utils.workshop.workshop_content import classify_item, preset_files, read_item_title
from frontengine.utils.workshop.workshop_manifest import checked_tree, read_manifest, safe_path
from frontengine.utils.workshop.workshop_package import _validate_pet, validate_content
from frontengine.utils.workshop.workshop_publications import PublicationStore, fingerprints, item_id


def validate_installed(root: Path) -> dict:
    """Retain bounded legacy import support without accepting arbitrary metadata."""
    checked_tree(root)
    if (root / "workshop.json").exists():
        return validate_content(root)
    kind = classify_item(root)
    if kind in ("pet_pack", "media"):
        _validate_pet(root)
    elif kind == "preset" and preset_files(root):
        pass
    else:
        raise ValueError("This Workshop content format is unsupported")
    return {"kind": kind, "title": read_item_title(root), "legacy": True}


class WorkshopCache:
    """Keep version directories alive for open scenes; never edit Steam-owned files."""

    def __init__(self, user_id: int, root: Path | None = None) -> None:
        self.root = safe_path(PublicationStore(user_id, root).root.parent, "subscriptions")
        self.root.mkdir(exist_ok=True)

    def directory(self, published_id: str) -> Path:
        return safe_path(self.root, str(item_id(published_id)))

    def current(self, published_id: str) -> dict | None:
        directory = self.directory(published_id)
        index = safe_path(directory, "current.json")
        if not index.exists():
            return None
        if index.stat().st_size > 1024 * 1024:
            raise ValueError("Workshop cache index is oversized")
        value = json.loads(index.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or not isinstance(value.get("hashes"), dict):
            raise ValueError("Invalid Workshop cache index")
        path = safe_path(directory, value.get("version"))
        manifest = validate_installed(path)
        return {**value, "id": str(item_id(published_id)), "path": str(path),
                "kind": manifest["kind"], "title": manifest["title"]}

    def stage(self, item: dict) -> dict:
        """Copy and validate a complete version before changing the active pointer."""
        published_id = str(item_id(item["id"]))
        if not item.get("path") or not item["state"] & 4 or item["state"] & (8 | 16 | 32):
            raise ValueError("Workshop content is still downloading or needs an update")
        source = Path(item["path"])
        manifest = validate_installed(source)
        hashes = fingerprints(source)
        version = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
        directory = self.directory(published_id)
        directory.mkdir(exist_ok=True)
        target = safe_path(directory, version)
        if not target.exists():
            with tempfile.TemporaryDirectory(prefix=".download-", dir=directory) as temporary:
                staging = Path(temporary) / "content"
                staging.mkdir()
                for path in checked_tree(source):
                    output = staging / path.relative_to(source)
                    output.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, output)
                validate_installed(staging)
                if fingerprints(staging) != hashes:
                    raise ValueError("Steam content changed during copying; retry after download completes")
                os.rename(staging, target)
        elif fingerprints(target) != hashes:
            raise ValueError("A cached version has local changes; restore or import it separately")
        candidate = {"id": published_id, "version": version, "hashes": hashes,
                     "timestamp": item.get("timestamp", 0), "kind": manifest["kind"],
                     "title": manifest["title"], "path": str(target), "status": "ready"}
        current = self.current(published_id)
        if current and fingerprints(Path(current["path"])) != current["hashes"]:
            return {**candidate, "status": "conflict", "current_path": current["path"]}
        self.activate(candidate)
        return candidate

    def activate(self, candidate: dict) -> None:
        """Explicit conflict resolution selects a version without deleting old leases."""
        directory = self.directory(candidate["id"])
        path = safe_path(directory, candidate["version"])
        validate_installed(path)
        if fingerprints(path) != candidate["hashes"]:
            raise ValueError("Cached content changed before activation")
        temporary = safe_path(directory, "current.tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump({key: candidate[key] for key in ("version", "hashes", "timestamp")}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, safe_path(directory, "current.json"))

    def entry(self, item: dict) -> Path:
        root = Path(item["path"])
        if (root / "workshop.json").exists():
            return safe_path(root, read_manifest(root)["entry"])
        return root
