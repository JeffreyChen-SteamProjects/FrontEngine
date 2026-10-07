"""Bounded command preferences and Unicode-aware local search."""
from __future__ import annotations

import unicodedata
from typing import Callable

from frontengine.utils.actions.action_registry import Action, ActionRegistry

SETTING_KEY = "command_palette"


def search_text(value: str) -> str:
    """Fold case, accents and compatibility characters for command search."""
    return "".join(char for char in unicodedata.normalize("NFKD", value.casefold())
                   if not unicodedata.combining(char))


class CommandHistory:
    """Persist stable IDs only; arguments and search text stay out of history."""

    def __init__(self, settings: dict, save: Callable[[], object]) -> None:
        self.settings, self.save = settings, save

    def values(self, key: str, known: set[str]) -> list[str]:
        """Ignore malformed, duplicate and unavailable persisted identifiers."""
        state = self.settings.get(SETTING_KEY, {})
        raw = state.get(key, []) if isinstance(state, dict) else []
        if not isinstance(raw, list):
            return []
        limit = 20 if key == "recent" else 200
        result = []
        for identifier in raw[:1000]:
            if isinstance(identifier, str) and identifier in known and identifier not in result:
                result.append(identifier)
            if len(result) >= limit:
                break
        return result

    def _store(self, key: str, values: list[str], known: set[str]) -> None:
        """Normalize both lists before saving; never retain command arguments."""
        state = {name: self.values(name, known) for name in ("recent", "favorites")}
        state[key] = values
        self.settings[SETTING_KEY] = state
        self.save()

    def record(self, identifier: str, known: set[str]) -> None:
        """Keep at most twenty most recently executed registered commands."""
        if identifier in known:
            recent = self.values("recent", known)
            self._store("recent", [identifier] + [item for item in recent if item != identifier][:19], known)

    def toggle_favorite(self, identifier: str, known: set[str]) -> None:
        """Toggle a favorite while bounding persisted preference size."""
        if identifier not in known:
            return
        favorites = self.values("favorites", known)
        if identifier in favorites:
            favorites.remove(identifier)
        elif len(favorites) < 200:
            favorites.append(identifier)
        self._store("favorites", favorites, known)

    def search(self, registry: ActionRegistry, query: str, label: Callable[[Action], str],
               favorites_only: bool = False) -> list[Action]:
        """Search the current language, fallback and IDs; rank favorites/recent first."""
        known = set(registry.actions)
        favorites, recent = self.values("favorites", known), self.values("recent", known)
        terms = search_text(query).split()
        actions = [action for action in registry.actions.values()
                   if (not favorites_only or action.identifier in favorites)
                   and all(term in search_text(f"{label(action)} {action.fallback} {action.identifier}")
                           for term in terms)]
        return sorted(actions, key=lambda action: (
            action.identifier not in favorites,
            recent.index(action.identifier) if action.identifier in recent else 20,
            label(action).casefold()))
