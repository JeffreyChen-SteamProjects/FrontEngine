"""Bounded persistent color collections and deterministic CSS/JSON export."""
from __future__ import annotations

import copy
import json
import os
import re
import tempfile
import unicodedata
import uuid
from pathlib import Path
from contextlib import nullcontext
from functools import wraps
from typing import Callable

MAX_SWATCHES = 512
MAX_RECENT = 50
SETTING_KEY = "color_palette"


def normalize_color(value: str) -> str:
    """Accept hexadecimal RGB only, expanding shorthand to a canonical value."""
    if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?", value):
        raise ValueError("Use #RRGGBB or #RGB")
    value = value.lower()
    return "#" + "".join(char * 2 for char in value[1:]) if len(value) == 4 else value


def _checked_name(value: str, optional: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError("Name and group must be text")
    value = value.strip()
    if (not value and not optional) or len(value) > 64 or any(ord(char) < 32 for char in value):
        raise ValueError("Names must contain 1–64 characters; groups may be empty")
    return value


def _identity(entry: dict) -> tuple[str, str]:
    return tuple(unicodedata.normalize("NFKC", entry[key]).casefold() for key in ("group", "name"))


def _palette_operation(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self._owner._settings_transaction() if self._owner is not None else nullcontext():
            if self._owner is not None:
                self._entries, self._recent, self._load_errors = [], [], 0
                self._load(self.settings.get(SETTING_KEY, {}))
            return method(self, *args, **kwargs)
    return call


class ColorPalette:
    """Keep at most 512 named swatches and 50 distinct recent sampled colors."""

    def __init__(self, settings: dict, save: Callable[[], object]) -> None:
        self._owner = None
        self.settings, self.save = settings, save
        self._entries: list[dict] = []
        self._recent: list[str] = []
        self._load_errors = 0
        self._load(settings.get(SETTING_KEY, {}))

    @classmethod
    def for_storage(cls, storage) -> ColorPalette:
        """Capture the owner and refresh cached values inside each transaction."""
        with storage._settings_transaction():
            palette = cls(storage.settings, storage.save_settings)
            palette._owner = storage
            return palette

    @property
    @_palette_operation
    def entries(self) -> list[dict]:
        return copy.deepcopy(self._entries) if self._owner is not None else self._entries

    @property
    @_palette_operation
    def recent(self) -> list[str]:
        return list(self._recent) if self._owner is not None else self._recent

    @property
    @_palette_operation
    def load_errors(self) -> int:
        return self._load_errors

    def _validate_entry(self, entry: dict, existing: list[dict]) -> dict:
        if not isinstance(entry, dict):
            raise ValueError("A swatch must be an object")
        identifier = entry.get("id")
        if not isinstance(identifier, str) or not re.fullmatch("[0-9a-f]{32}", identifier):
            raise ValueError("Invalid swatch identity")
        checked = {"id": identifier, "name": _checked_name(entry.get("name")),
                   "group": _checked_name(entry.get("group", ""), True),
                   "color": normalize_color(entry.get("color"))}
        if any(item["id"] == identifier or _identity(item) == _identity(checked) for item in existing):
            raise ValueError("This group already contains that name")
        return checked

    def _load(self, state) -> None:
        if not isinstance(state, dict):
            self._load_errors += 1
            return
        if (type(state.get("version", 1)) is not int or state.get("version", 1) != 1 or
                state.get("format", "frontengine.palette") != "frontengine.palette"):
            self._load_errors += 1
            return
        entries, recent = state.get("swatches", []), state.get("recent", [])
        if not isinstance(entries, list) or not isinstance(recent, list):
            self._load_errors += 1
            return
        for entry in entries[:MAX_SWATCHES]:
            try:
                self._entries.append(self._validate_entry(entry, self._entries))
            except ValueError:
                self._load_errors += 1
        self._load_errors += max(0, len(entries) - MAX_SWATCHES)
        for value in recent[:MAX_RECENT]:
            try:
                value = normalize_color(value)
                if value not in self._recent:
                    self._recent.append(value)
            except ValueError:
                self._load_errors += 1

    def _commit(self, entries: list[dict], recent: list[str]) -> None:
        state = {"format": "frontengine.palette", "version": 1,
                 "swatches": copy.deepcopy(entries), "recent": list(recent)}
        previous = self.settings.get(SETTING_KEY)
        self.settings[SETTING_KEY] = state
        try:
            self.save()
        except Exception:
            if previous is None:
                self.settings.pop(SETTING_KEY, None)
            else:
                self.settings[SETTING_KEY] = previous
            raise
        self._entries, self._recent = entries, recent
        self._load_errors = 0

    @_palette_operation
    def add(self, name: str, group: str, color: str) -> str:
        """Add a named swatch; duplicate names within a group are rejected."""
        if len(self._entries) >= MAX_SWATCHES:
            raise ValueError("The palette contains 512 colors")
        entry = self._validate_entry({"id": uuid.uuid4().hex, "name": name, "group": group,
                                      "color": color}, self._entries)
        self._commit([*self._entries, entry], list(self._recent))
        return entry["id"]

    @_palette_operation
    def update(self, identifier: str, name: str, group: str, color: str) -> None:
        """Validate all edited values before replacing the existing swatch."""
        if not any(entry["id"] == identifier for entry in self._entries):
            raise ValueError("Swatch no longer exists")
        others = [entry for entry in self._entries if entry["id"] != identifier]
        updated = self._validate_entry({"id": identifier, "name": name, "group": group, "color": color}, others)
        self._commit([updated if entry["id"] == identifier else entry for entry in self._entries], list(self._recent))

    @_palette_operation
    def remove(self, identifier: str) -> None:
        """Delete only the identified swatch; sampled recent colors remain reusable."""
        self._commit([entry for entry in self._entries if entry["id"] != identifier], list(self._recent))

    @_palette_operation
    def sample(self, color: str) -> str:
        """Collect consecutive clicks, reusing an existing swatch for the same RGB."""
        color = normalize_color(color)
        existing = next((entry for entry in self._entries if entry["color"] == color), None)
        recent = [color, *[value for value in self._recent if value != color]][:MAX_RECENT]
        entries = list(self._entries)
        if existing is None:
            if len(entries) >= MAX_SWATCHES:
                raise ValueError("The palette contains 512 colors")
            names = {_identity(entry) for entry in entries}
            number = 1
            while ("", f"color-{number}") in names:
                number += 1
            existing = {"id": uuid.uuid4().hex, "name": f"color-{number}", "group": "", "color": color}
            entries.append(existing)
        self._commit(entries, recent)
        return existing["id"]

    @_palette_operation
    def export_text(self, format_name: str) -> str:
        """Export exact RGB values, making colliding CSS slugs distinct."""
        if format_name == "json":
            return json.dumps({"format": "frontengine.palette", "version": 1,
                               "swatches": self._entries, "recent": self._recent}, ensure_ascii=False, indent=2) + "\n"
        if format_name != "css":
            raise ValueError("Choose CSS or JSON")
        used, lines = set(), [":root {"]
        for entry in self._entries:
            label = "-".join(value for value in (entry["group"], entry["name"]) if value)
            ascii_name = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode()
            base = re.sub(r"[^a-z0-9_-]+", "-", ascii_name.lower()).strip("-") or "color"
            name, number = base, 2
            while name in used:
                name, number = f"{base}-{number}", number + 1
            used.add(name)
            lines.append(f"  --{name}: {entry['color']};")
        return "\n".join([*lines, "}", ""])

    @_palette_operation
    def export(self, target: Path, format_name: str) -> None:
        """Write next to the target and replace only after successful serialization."""
        from frontengine.user_setting.storage_session import checked_export_destination
        target = checked_export_destination(target)
        text = self.export_text(format_name)
        descriptor, temporary = tempfile.mkstemp(prefix=".palette-", dir=target.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            Path(temporary).unlink(missing_ok=True)
