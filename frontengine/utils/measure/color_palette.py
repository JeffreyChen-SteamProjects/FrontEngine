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


class ColorPalette:
    """Keep at most 512 named swatches and 50 distinct recent sampled colors."""

    def __init__(self, settings: dict, save: Callable[[], object]) -> None:
        self.settings, self.save = settings, save
        self.entries: list[dict] = []
        self.recent: list[str] = []
        self.load_errors = 0
        self._load(settings.get(SETTING_KEY, {}))

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
            self.load_errors += 1
            return
        if (type(state.get("version", 1)) is not int or state.get("version", 1) != 1 or
                state.get("format", "frontengine.palette") != "frontengine.palette"):
            self.load_errors += 1
            return
        entries, recent = state.get("swatches", []), state.get("recent", [])
        if not isinstance(entries, list) or not isinstance(recent, list):
            self.load_errors += 1
            return
        for entry in entries[:MAX_SWATCHES]:
            try:
                self.entries.append(self._validate_entry(entry, self.entries))
            except ValueError:
                self.load_errors += 1
        self.load_errors += max(0, len(entries) - MAX_SWATCHES)
        for value in recent[:MAX_RECENT]:
            try:
                value = normalize_color(value)
                if value not in self.recent:
                    self.recent.append(value)
            except ValueError:
                self.load_errors += 1

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
        self.entries, self.recent = entries, recent
        self.load_errors = 0

    def add(self, name: str, group: str, color: str) -> str:
        """Add a named swatch; duplicate names within a group are rejected."""
        if len(self.entries) >= MAX_SWATCHES:
            raise ValueError("The palette contains 512 colors")
        entry = self._validate_entry({"id": uuid.uuid4().hex, "name": name, "group": group,
                                      "color": color}, self.entries)
        self._commit([*self.entries, entry], list(self.recent))
        return entry["id"]

    def update(self, identifier: str, name: str, group: str, color: str) -> None:
        """Validate all edited values before replacing the existing swatch."""
        if not any(entry["id"] == identifier for entry in self.entries):
            raise ValueError("Swatch no longer exists")
        others = [entry for entry in self.entries if entry["id"] != identifier]
        updated = self._validate_entry({"id": identifier, "name": name, "group": group, "color": color}, others)
        self._commit([updated if entry["id"] == identifier else entry for entry in self.entries], list(self.recent))

    def remove(self, identifier: str) -> None:
        """Delete only the identified swatch; sampled recent colors remain reusable."""
        self._commit([entry for entry in self.entries if entry["id"] != identifier], list(self.recent))

    def sample(self, color: str) -> str:
        """Collect consecutive clicks, reusing an existing swatch for the same RGB."""
        color = normalize_color(color)
        existing = next((entry for entry in self.entries if entry["color"] == color), None)
        recent = [color, *[value for value in self.recent if value != color]][:MAX_RECENT]
        entries = list(self.entries)
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

    def export_text(self, format_name: str) -> str:
        """Export exact RGB values, making colliding CSS slugs distinct."""
        if format_name == "json":
            return json.dumps({"format": "frontengine.palette", "version": 1,
                               "swatches": self.entries, "recent": self.recent}, ensure_ascii=False, indent=2) + "\n"
        if format_name != "css":
            raise ValueError("Choose CSS or JSON")
        used, lines = set(), [":root {"]
        for entry in self.entries:
            label = "-".join(value for value in (entry["group"], entry["name"]) if value)
            ascii_name = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode()
            base = re.sub(r"[^a-z0-9_-]+", "-", ascii_name.lower()).strip("-") or "color"
            name, number = base, 2
            while name in used:
                name, number = f"{base}-{number}", number + 1
            used.add(name)
            lines.append(f"  --{name}: {entry['color']};")
        return "\n".join([*lines, "}", ""])

    def export(self, target: Path, format_name: str) -> None:
        """Write next to the target and replace only after successful serialization."""
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
