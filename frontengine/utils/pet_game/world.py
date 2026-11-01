"""The home world: state, player commands and the versioned save snapshot.

UI code sends commands here and reads state; only ``simulation.advance`` moves
time. Commands return a short result code instead of raising for ordinary
refusals, so the interface can explain them. Identifiers are stable counters,
never screen or list indices.
"""
from __future__ import annotations

import re
from collections import deque

from frontengine.utils.pet_game.behaviour import cancel_activity, refusal, start
from frontengine.utils.pet_game.catalog import (
    CELL_PIXELS, STARTER_COINS, STARTER_KIT, Catalog, FurnitureDefinition,
)
from frontengine.utils.pet_game.jobs import MAX_TASKS, MAX_UNITS, Task
from frontengine.utils.pet_game.layout import (
    MAX_FURNITURE, Furniture, Zone, placement_problem,
)
from frontengine.utils.pet_game.ledger import Ledger
from frontengine.utils.pet_game.resident import Resident, resident_from_profile
from frontengine.utils.pet_game.rng import GameRandom
from frontengine.utils.pet_game.schedule import TEMPLATES, initial_time

FORMAT = "frontengine.pet-home"
VERSION = 1
MODES = ("manage", "sandbox")
MAX_RESIDENTS = 12
MAX_ZONES = 8
COMMANDS = ("sleep", "eat", "play", "relax", "work", "stop")
_HOME = re.compile(r"[0-9a-f]{32}")


def furniture_item(definition: str) -> str:
    return "furniture:" + definition


class World:
    """All home state. Not thread-safe: the owning service calls it on one thread."""

    def __init__(self, catalog: Catalog, home: str, mode: str = "manage", seed: int = 1) -> None:
        if not isinstance(home, str) or not _HOME.fullmatch(home) or mode not in MODES:
            raise ValueError("Invalid home identity or mode")
        self.catalog = catalog
        self.home = home
        self.mode = mode
        self.time_ms = initial_time()
        self.rng = GameRandom(seed)
        self.next_id = 1
        self.zones: dict[str, Zone] = {}
        self.furniture: dict[str, Furniture] = {}
        self.residents: dict[str, Resident] = {}
        self.tasks: dict[str, Task] = {}
        self.ledger = Ledger()
        self.flags: set[str] = set()
        self.dormant: list[dict] = []      # saved pieces whose content is not installed
        self.events: deque[dict] = deque(maxlen=200)
        self.carry_ms = 0

    @property
    def sandbox(self) -> bool:
        return self.mode == "sandbox"

    def _new_id(self, prefix: str) -> str:
        identifier = f"{prefix}{self.next_id}"
        self.next_id += 1
        return identifier

    def emit(self, kind: str, **values: object) -> None:
        self.events.append({"kind": kind, "time": self.time_ms, **values})

    def drain_events(self) -> list[dict]:
        events = list(self.events)
        self.events.clear()
        return events

    # ----- zones and furniture -------------------------------------------------

    def add_zone(self, screen: str, x: int, y: int, width_cells: int) -> str:
        if len(self.zones) >= MAX_ZONES:
            raise ValueError("Too many home zones")
        identifier = self._new_id("z")
        zone = Zone.from_dict({"id": identifier, "screen": screen, "x": x, "y": y,
                               "width_cells": width_cells, "theme": "warm_home",
                               "entrance": 0, "restricted": []})
        self.zones[identifier] = zone
        return identifier

    def grant_starter_kit(self) -> str:
        """Initial coins and basic furniture, at most once per home even if rerun."""
        result = self.ledger.apply("starter-kit", "starter", STARTER_COINS, STARTER_KIT)
        self.flags.add("starter_kit")
        return result

    def definition(self, furniture: Furniture) -> FurnitureDefinition:
        return self.catalog.furniture[furniture.definition]

    def in_zone(self, zone: str, exclude: str | None = None) -> list[tuple[Furniture, FurnitureDefinition]]:
        return [(piece, self.definition(piece)) for piece in self.furniture.values()
                if piece.zone == zone and piece.identifier != exclude]

    def stored(self, definition: str) -> int:
        return self.ledger.available(furniture_item(definition))

    def preview(self, definition: str, zone: str, cell: int, moving: str | None = None) -> str | None:
        """Explain why a placement would fail without changing anything."""
        found = self.catalog.furniture.get(definition)
        if found is None or zone not in self.zones:
            return "unknown"
        return placement_problem(self.zones[zone], found, cell, self.in_zone(zone, moving))

    def buy(self, definition: str, transaction: str) -> str:
        found = self.catalog.furniture.get(definition)
        if found is None:
            return "unknown"
        if found.essential:
            return "not_for_sale"
        if self.sandbox:
            return "accepted"
        result = self.ledger.apply(transaction, "buy:" + definition, -found.price,
                                   {furniture_item(definition): 1})
        return "insufficient_coins" if result == "insufficient" else result

    def sell(self, definition: str, transaction: str) -> str:
        found = self.catalog.furniture.get(definition)
        if found is None:
            return "unknown"
        if found.essential:
            return "essential"
        if self.sandbox:
            return "accepted"
        result = self.ledger.apply(transaction, "sell:" + definition, found.sell_back,
                                   {furniture_item(definition): -1})
        return "none_stored" if result == "insufficient" else result

    def place(self, definition: str, zone: str, cell: int, flipped: bool = False) -> tuple[str, str | None]:
        problem = self.preview(definition, zone, cell)
        if problem is not None:
            return problem, None
        if len(self.furniture) >= MAX_FURNITURE:
            return "too_many", None
        identifier = self._new_id("f")
        if not self.sandbox:
            result = self.ledger.apply("place:" + identifier, "place",
                                       items={furniture_item(definition): -1})
            if result != "accepted":
                return "none_stored", None
        self.furniture[identifier] = Furniture(identifier, definition, zone, cell, bool(flipped))
        self.emit("placed", furniture=identifier, definition=definition)
        return "accepted", identifier

    def move(self, identifier: str, cell: int, flipped: bool | None = None, zone: str | None = None) -> str:
        piece = self.furniture.get(identifier)
        if piece is None:
            return "unknown"
        target = zone or piece.zone
        problem = self.preview(piece.definition, target, cell, moving=identifier)
        if problem is not None:
            return problem
        self.interrupt_users(identifier, "furniture_moved")
        piece.zone, piece.cell = target, cell
        if flipped is not None:
            piece.flipped = bool(flipped)
        return "accepted"

    def store(self, identifier: str) -> str:
        """Put a piece back in storage; work at it pauses with its progress kept."""
        piece = self.furniture.get(identifier)
        if piece is None:
            return "unknown"
        if not self.sandbox:
            result = self.ledger.apply("store:" + identifier, "store",
                                       items={furniture_item(piece.definition): 1})
            if result not in ("accepted", "duplicate"):
                return result
        self.interrupt_users(identifier, "furniture_stored")
        for task in self.tasks.values():
            if task.station == identifier and task.open:
                task.station = None
                task.state = "paused"
        del self.furniture[identifier]
        return "accepted"

    def assign_bed(self, identifier: str, resident: str | None) -> str:
        piece = self.furniture.get(identifier)
        if piece is None or self.definition(piece).category != "bed":
            return "unknown"
        if resident is not None and resident not in self.residents:
            return "unknown"
        for other in self.furniture.values():
            if resident is not None and other.owner == resident:
                other.owner = None
        piece.owner = resident
        return "accepted"

    def interrupt_users(self, identifier: str, reason: str) -> None:
        for resident in self.residents.values():
            if resident.activity is not None and resident.activity.furniture == identifier:
                cancel_activity(self, resident, reason)

    def comfort(self, zone: str) -> int:
        return min(10, sum(definition.comfort for _piece, definition in self.in_zone(zone)))

    # ----- residents -------------------------------------------------------------

    def add_resident(self, profile: dict, zone: str) -> str:
        """Adopt a validated pet profile; the same identity can live here only once."""
        if profile["id"] in self.residents:
            return "duplicate"
        if len(self.residents) >= MAX_RESIDENTS or zone not in self.zones:
            return "unavailable"
        entrance = self.zones[zone].entrance
        x_milli = (entrance * CELL_PIXELS + CELL_PIXELS // 2) * 1000
        self.residents[profile["id"]] = resident_from_profile(profile, zone, x_milli)
        self.emit("arrived", resident=profile["id"])
        return "accepted"

    def remove_resident(self, identifier: str) -> str:
        resident = self.residents.get(identifier)
        if resident is None:
            return "unknown"
        for task in list(self.tasks.values()):
            if task.resident == identifier:
                self.cancel_task(task.identifier)
        cancel_activity(self, resident, "left_home")
        for piece in self.furniture.values():
            if piece.owner == identifier:
                piece.owner = None
        del self.residents[identifier]
        return "accepted"

    def command(self, identifier: str, command: str) -> str:
        """Queue a direct instruction; it outranks needs but not safety or exhaustion."""
        resident = self.residents.get(identifier)
        if resident is None or command not in COMMANDS:
            return "unknown"
        if resident.parked or resident.away:
            return "parked"
        if command == "stop":
            resident.commands.clear()
            cancel_activity(self, resident, "command_stop")
            return "accepted"
        reason = refusal(self, resident, command)
        if reason is not None:
            resident.last_refusal = reason
            self.emit("refused", resident=identifier, command=command, reason=reason)
            return reason
        resident.commands[:] = [command]
        cancel_activity(self, resident, "command")
        resident.decide_after_ms = 0
        return "accepted"

    def drag(self, identifier: str, x_milli: int | None) -> str:
        """Start a drag with None; finish by dropping at a zone-local position."""
        resident = self.residents.get(identifier)
        if resident is None:
            return "unknown"
        if x_milli is None:
            cancel_activity(self, resident, "dragged")
            start(self, resident, "drag", "dragged")
            return "accepted"
        width = self.zones[resident.zone].width_pixels * 1000
        resident.x_milli = max(0, min(width - 1, int(x_milli)))
        if resident.activity is not None and resident.activity.kind == "drag":
            resident.activity = None
        return "accepted"

    def park(self, identifier: str, parked: bool) -> str:
        """A hidden resident stops in place, releasing furniture; others keep living."""
        resident = self.residents.get(identifier)
        if resident is None:
            return "unknown"
        if parked:
            cancel_activity(self, resident, "parked")
            resident.commands.clear()
        resident.parked = bool(parked)
        return "accepted"

    def set_routine(self, identifier: str, routine: str) -> str:
        resident = self.residents.get(identifier)
        if resident is None or routine not in TEMPLATES:
            return "unknown"
        resident.routine = routine
        return "accepted"

    # ----- work -------------------------------------------------------------------

    def create_task(self, recipe: str, resident: str, units: int = 1, station: str | None = None,
                    priority: int = 5) -> tuple[str, str | None]:
        found = self.catalog.recipes.get(recipe)
        member = self.residents.get(resident)
        if found is None or member is None:
            return "unknown", None
        if type(units) is not int or not 1 <= units <= MAX_UNITS or not 0 <= priority <= 9:
            return "invalid", None
        if member.level(found.profession) < found.min_level:
            return "skill_too_low", None
        if station is not None:
            piece = self.furniture.get(station)
            if piece is None or self.definition(piece).profession != found.profession:
                return "wrong_station", None
        if sum(task.open for task in self.tasks.values()) >= MAX_TASKS:
            return "too_many", None
        identifier = self._new_id("t")
        self.tasks[identifier] = Task(identifier, recipe, resident, station, units, priority=priority)
        return "accepted", identifier

    def cancel_task(self, identifier: str) -> str:
        """Unfinished units never pay; reserved inputs return to the inventory in full."""
        task = self.tasks.get(identifier)
        if task is None or not task.open:
            return "unknown"
        resident = self.residents.get(task.resident)
        if resident is not None and resident.activity is not None and resident.activity.task == identifier:
            cancel_activity(self, resident, "task_cancelled")
        if task.inputs_reserved:
            self.ledger.release(self.catalog.recipes[task.recipe].inputs)
            task.inputs_reserved = False
        task.state = "cancelled"
        del self.tasks[identifier]
        return "accepted"

    def open_tasks(self, resident: str) -> list[Task]:
        return sorted((task for task in self.tasks.values() if task.resident == resident and task.open),
                      key=lambda task: (-task.priority, int(task.identifier[1:])))
