"""Arranging a whole zone at once: undo and redo, layout codes to copy and paste, ready-made layouts.

A layout is a list of ``(definition, cell, flipped)`` placements. Applying one puts
every piece of the zone back in storage and sets the layout out again, buying what
is missing first when asked; nothing here bypasses ``World.buy``/``place``/``store``,
so prices, unlocks, storage counts and the ledger's idempotence still hold.
"""
from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy
from typing import TYPE_CHECKING

from frontengine.utils.pet_game.goals import unlocked

if TYPE_CHECKING:
    from frontengine.utils.pet_game.world import World

LAYOUT_FORMAT = "frontengine.home-layout"
MAX_LAYOUT_PIECES = 64
MAX_LAYOUT_TEXT = 16 * 1024
HISTORY_LIMIT = 30

# Ready-made layouts for a home at least 24 cells wide (the entrance is cell 0).
PRESETS: dict[str, tuple[tuple[str, int, bool], ...]] = {
    "starter": (("bed_basic", 1, False), ("table_basic", 6, False), ("desk_basic", 11, False),
                ("plant_pot", 15, False)),
    "cozy": (("bed_cozy", 1, False), ("rug", 6, False), ("armchair", 6, False), ("wall_lamp", 9, False),
             ("table_basic", 11, False), ("desk_basic", 16, False), ("plant_pot", 20, False),
             ("pet_cushion", 21, False)),
    "workshop": (("bed_basic", 1, False), ("table_basic", 6, False), ("workbench", 11, False),
                 ("stool", 15, False), ("desk_basic", 17, False), ("toy_box", 21, False)),
    "garden": (("bed_basic", 1, False), ("snack_bar", 6, False), ("planter", 9, False), ("plant_pot", 12, False),
               ("desk_basic", 14, False), ("bean_bag", 18, False), ("plant_pot", 21, False)),
}


def _stairs_first(world: World, names) -> list[int]:
    """Placement order: pet stairs before anything else, so a raised piece beside them is reachable."""
    names = list(names)
    steps = [world.catalog.furniture.get(name) is not None and world.catalog.furniture[name].steps for name in names]
    return sorted(range(len(names)), key=lambda index: not steps[index])


def layout_of(world: World, zone: str) -> list[tuple[str, int, bool]]:
    return sorted((piece.definition, piece.cell, piece.flipped) for piece, _definition in world.in_zone(zone))


def snapshot(world: World, zone: str) -> list[dict]:
    """Everything needed to put the zone back: definition, cell, mirroring and the bed's owner."""
    return [{"definition": piece.definition, "cell": piece.cell, "flipped": piece.flipped, "owner": piece.owner}
            for piece, _definition in sorted(world.in_zone(zone), key=lambda item: item[0].cell)]


def restore(world: World, zone: str, saved: list[dict]) -> int:
    """Put the zone back; nonzero means a storage or placement operation failed."""
    for piece, _definition in list(world.in_zone(zone)):
        if world.store(piece.identifier) != "accepted":
            return 1
    missed = 0
    for entry in (saved[index] for index in _stairs_first(world, (entry["definition"] for entry in saved))):
        result, identifier = world.place(entry["definition"], zone, entry["cell"], entry["flipped"])
        if result != "accepted":
            missed += 1
        elif entry.get("owner") in world.residents:
            world.assign_bed(identifier, entry["owner"])
    return missed


class LayoutHistory:
    """Undo and redo for layout changes made from the page; kept in memory for the session."""

    def __init__(self, limit: int = HISTORY_LIMIT) -> None:
        self.limit = limit
        self._undo: list[list[dict]] = []
        self._redo: list[list[dict]] = []

    def record(self, world: World, zone: str) -> None:
        """Call before a change: the current layout becomes the step to go back to."""
        self._undo.append(snapshot(world, zone))
        del self._undo[:-self.limit]
        self._redo.clear()

    def can_undo(self) -> bool:
        return bool(self._undo)

    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo(self, world: World, zone: str) -> bool:
        if not self._undo:
            return False
        trial = deepcopy(world, {id(world.catalog): world.catalog})
        if restore(trial, zone, self._undo[-1]):
            return False
        self._redo.append(snapshot(world, zone))
        restore(world, zone, self._undo.pop())
        return True

    def redo(self, world: World, zone: str) -> bool:
        if not self._redo:
            return False
        trial = deepcopy(world, {id(world.catalog): world.catalog})
        if restore(trial, zone, self._redo[-1]):
            return False
        self._undo.append(snapshot(world, zone))
        restore(world, zone, self._redo.pop())
        return True


def encode_layout(world: World, zone: str) -> str:
    """A layout code to copy: plain JSON, no residents, coins or anything personal."""
    return json.dumps({"format": LAYOUT_FORMAT, "version": 1,
                       "pieces": [[name, cell, flipped] for name, cell, flipped in layout_of(world, zone)]},
                      separators=(",", ":"))


def decode_layout(text: str, catalog) -> list[tuple[str, int, bool]]:
    """Validate a pasted layout code at the boundary; anything unexpected is rejected, not trusted."""
    if not isinstance(text, str) or len(text) > MAX_LAYOUT_TEXT:
        raise ValueError("Layout code too large")
    data = json.loads(text)
    if not isinstance(data, dict) or data.get("format") != LAYOUT_FORMAT or data.get("version") != 1:
        raise ValueError("Not a FrontEngine home layout")
    pieces = data.get("pieces")
    if not isinstance(pieces, list) or len(pieces) > MAX_LAYOUT_PIECES:
        raise ValueError("Invalid layout pieces")
    result = []
    for entry in pieces:
        if (not isinstance(entry, list) or len(entry) != 3 or entry[0] not in catalog.furniture
                or type(entry[1]) is not int or not 0 <= entry[1] <= 1000 or type(entry[2]) is not bool):
            raise ValueError("Invalid layout piece")
        result.append((entry[0], entry[1], entry[2]))
    return result


def plan(world: World, zone: str, pieces) -> tuple[dict[str, int], int, dict[str, int]]:
    """``(missing, cost, unavailable)``: what the layout needs beyond storage plus this zone, the coins
    to buy the buyable part, and what cannot be bought (essential, locked or unknown)."""
    need = Counter(name for name, _cell, _flipped in pieces)
    have = Counter({name: world.stored(name) for name in need})
    have.update(piece.definition for piece, _definition in world.in_zone(zone))
    missing = {name: need[name] - have[name] for name in need if need[name] > have[name]}
    if world.sandbox:
        return {}, 0, {}
    cost, unavailable = 0, {}
    for name, count in missing.items():
        definition = world.catalog.furniture.get(name)
        if definition is None or definition.essential or not unlocked(world, definition.unlock_level):
            unavailable[name] = count
        else:
            cost += definition.price * count
    return missing, cost, unavailable


def apply_layout(world: World, zone: str, pieces, transaction: str, buy_missing: bool = False) -> tuple[str, int]:
    """Set a layout out; ``("accepted", skipped)`` or why nothing changed (``insufficient_coins``)."""
    missing, cost, unavailable = plan(world, zone, pieces)
    if buy_missing and missing:
        if cost > world.ledger.coins:
            return "insufficient_coins", len(pieces)
        for name, count in missing.items():
            if name in unavailable:
                continue
            for index in range(count):
                world.buy(name, f"{transaction}:{name}:{index}")
    for piece, _definition in list(world.in_zone(zone)):
        world.store(piece.identifier)
    pieces = list(pieces)
    ordered = (pieces[index] for index in _stairs_first(world, (name for name, _cell, _flipped in pieces)))
    skipped = sum(1 for name, cell, flipped in ordered if world.place(name, zone, cell, flipped)[0] != "accepted")
    return "accepted", skipped
