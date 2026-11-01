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
from frontengine.utils.pet_game.goals import Progress, unlocked
from frontengine.utils.pet_game.catalog import (
    CELL_PIXELS, STARTER_COINS, STARTER_KIT, Catalog, FurnitureDefinition,
)
from frontengine.utils.pet_game.jobs import MAX_TASKS, MAX_UNITS, Task
from frontengine.utils.pet_game.layout import (
    AREA_TAGS, MAX_FURNITURE, MAX_ZONE_CELLS, MIN_ZONE_CELLS, THEMES, Furniture, Zone, can_climb,
    has_steps, placement_problem,
)
from frontengine.utils.pet_companion.stats import MAX_AFFECTION
from frontengine.utils.pet_game.goals import MAX_STATION_LEVEL
from frontengine.utils.pet_game.ledger import Ledger
from frontengine.utils.pet_game.resident import Resident, resident_from_profile
from frontengine.utils.pet_game.rng import GameRandom
from frontengine.utils.pet_game.schedule import TEMPLATES, initial_time

FORMAT = "frontengine.pet-home"
VERSION = 6              # 2: needs, relationships; 3: goals, progress; 4: zone areas; 5: crossings; 6: upgrades
RELATION_LIMIT = 100
MODES = ("manage", "sandbox")
MAX_RESIDENTS = 12
MAX_ZONES = 8
COMMANDS = ("sleep", "eat", "play", "relax", "work", "stop")
# The player's own care: a small, immediate lift with a cooldown per pet and kind, so it never farms.
INTERACTIONS = {"feed": {"fullness": 15, "mood": 3}, "pat": {"mood": 8, "social": 5},
                "talk": {"social": 12, "mood": 3}}
INTERACT_COOLDOWN_MS = 30_000
UPGRADE_BASE_COINS = 80     # the basic desk is free, but its upgrades are not
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
        # Residents take jobs and rewards are collected by themselves. Runtime only, never saved:
        # tests of the bare mechanics switch it off.
        self.automatic = True
        self.offline_zones: set[str] = set()     # zones whose screen is disconnected (runtime only)
        self._offline_parked: set[str] = set()
        self._interacted: dict[tuple[str, str], int] = {}     # (resident, kind) -> game time, runtime only
        self.residents: dict[str, Resident] = {}
        self.tasks: dict[str, Task] = {}
        self.ledger = Ledger()
        self.flags: set[str] = set()
        self.dormant: list[dict] = []      # saved pieces whose content is not installed
        self.relations: dict[str, int] = {}  # "<uuid>|<uuid>" (sorted) -> -100..100
        self.social_ready: dict[str, int] = {}  # runtime cooldowns per pair
        self.progress = Progress()
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
        """Publish an event and count it for goals (counters persist, the event queue does not)."""
        self.events.append({"kind": kind, "time": self.time_ms, **values})
        self.progress.count(kind)
        detail = values.get("activity") if kind == "completed" else values.get("recipe")
        if kind in ("completed", "settled") and isinstance(detail, str):
            self.progress.count(f"{kind}:{detail}")
        if kind == "arrived" and isinstance(values.get("resident"), str):
            self.progress.arrivals.setdefault(values["resident"], self.time_ms)

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
                               "entrance": 0, "restricted": [], "areas": [], "link": None})
        self.zones[identifier] = zone
        return identifier

    def set_area(self, zone: str, first: int, last: int, tag: str | None) -> str:
        """Label part of a zone's floor (``None`` clears it); it steers choices, never forbids them."""
        if zone not in self.zones or (tag is not None and tag not in AREA_TAGS):
            return "unknown"
        self.zones[zone].areas = self.zones[zone].with_area(first, last, tag)
        return "accepted"

    def move_zone(self, zone: str, screen: str, x: int, y: int, width_cells: int) -> str:
        """Give a zone another screen or size; pieces that no longer fit go back to storage."""
        found = self.zones.get(zone)
        if found is None or not isinstance(screen, str) or len(screen) > 128:
            return "unknown"
        if any(other.screen == screen for key, other in self.zones.items() if key != zone):
            return "screen_taken"
        width = max(MIN_ZONE_CELLS, min(MAX_ZONE_CELLS, int(width_cells)))
        found.screen, found.x, found.y, found.width_cells = screen, int(x), int(y), width
        found.areas = tuple((first, min(last, width - 1), tag) for first, last, tag in found.areas if first < width)
        found.entrance = min(found.entrance, width - 1)
        for piece, definition in list(self.in_zone(zone)):
            if piece.cell + definition.width > width:
                self.store(piece.identifier)
        for resident in self.residents.values():
            if resident.zone == zone:
                resident.x_milli = min(resident.x_milli, found.width_pixels * 1000 - 1)
        return "accepted"

    def link_zones(self, zone: str, other: str | None) -> str:
        """Join two zones' entrances into a crossing point (``None`` removes the zone's crossing)."""
        if zone not in self.zones or (other is not None and (other not in self.zones or other == zone)):
            return "unknown"
        for key in (zone, other, self.zones[zone].link, self.zones[other].link if other else None):
            if key in self.zones and self.zones[key].link in (zone, other):
                self.zones[key].link = None
        self.zones[zone].link = other
        if other is not None:
            self.zones[other].link = zone
        return "accepted"

    def crossing(self, zone: str) -> str | None:
        """Where this zone's entrance leads, when that zone's screen is connected."""
        link = self.zones[zone].link if zone in self.zones else None
        return link if link in self.zones and link not in self.offline_zones else None

    def cross(self, identifier: str) -> str:
        """A pet walks through a crossing point by itself; it keeps its bed in the old zone."""
        resident = self.residents.get(identifier)
        target = self.crossing(resident.zone) if resident is not None else None
        if target is None:
            return "unknown"
        return self.transfer_resident(identifier, target, keep_claims=True)

    def transfer_resident(self, identifier: str, zone: str, keep_claims: bool = False) -> str:
        """Move a pet to another zone on purpose; it arrives at that zone's entrance."""
        resident = self.residents.get(identifier)
        if resident is None or zone not in self.zones:
            return "unknown"
        if resident.zone == zone:
            return "duplicate"
        cancel_activity(self, resident, "moved_zone")
        for piece in self.furniture.values():
            if piece.owner == identifier and piece.zone != zone and not keep_claims:
                piece.owner = None
        resident.zone = zone
        entrance = self.zones[zone].entrance
        resident.x_milli = (entrance * CELL_PIXELS + CELL_PIXELS // 2) * 1000
        self.emit("moved_zone", resident=identifier, zone=zone)
        return "accepted"

    def set_offline(self, zones: set[str]) -> list[str]:
        """Zones whose screen is gone: their pets wait, their furniture stays; nothing is copied.

        Returns the residents whose waiting state changed. Reconnecting the screen lets them
        carry on where they were.
        """
        zones = {zone for zone in zones if zone in self.zones}
        changed = []
        for identifier in sorted(self.residents):
            resident = self.residents[identifier]
            waiting = resident.zone in zones
            if waiting and not resident.parked:
                self.park(identifier, True)
                self._offline_parked.add(identifier)
                changed.append(identifier)
            elif not waiting and identifier in self._offline_parked:
                self.park(identifier, False)       # only pets this parked: a pet hidden on purpose stays
                self._offline_parked.discard(identifier)
                changed.append(identifier)
        self.offline_zones = zones
        return changed

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
        others = self.in_zone(zone, moving)
        problem = placement_problem(self.zones[zone], found, cell, others)
        if problem is None and not self._reachable_after(zone, found, cell, others):
            return "unreachable"
        return problem

    def _reachable_after(self, zone: str, definition, cell: int, others) -> bool:
        """Would every raised piece still be reachable with this piece at ``cell``?"""
        if any(can_climb(r.traits) for r in self.residents.values() if r.zone == zone):
            return True
        placed = Furniture("f0", definition.identifier, zone, cell)
        pieces = [*others, (placed, definition)]
        raised = [(piece, d) for piece, d in pieces if d.raised] if definition.steps else [(placed, definition)]
        return all(has_steps(piece, d, pieces) for piece, d in raised if d.raised)

    def reachable(self, resident, piece) -> bool:
        """Ground is always connected; a raised point needs climbing or pet stairs beside it."""
        definition = self.definition(piece)
        return (not definition.raised or can_climb(resident.traits)
                or has_steps(piece, definition, self.in_zone(piece.zone)))

    def buy(self, definition: str, transaction: str) -> str:
        found = self.catalog.furniture.get(definition)
        if found is None:
            return "unknown"
        if found.essential:
            return "not_for_sale"
        if self.sandbox:
            return "accepted"
        if not unlocked(self, found.unlock_level):
            return "locked"
        result = self.ledger.apply(transaction, "buy:" + definition, -found.price,
                                   {furniture_item(definition): 1})
        if result == "accepted":
            self.emit("bought", definition=definition)
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

    def buy_item(self, name: str, count: int, transaction: str) -> str:
        """Buy materials the shop sells; the price is always above what selling returns."""
        item = self.catalog.items.get(name)
        if item is None or not item.buy_price:
            return "not_for_sale"
        if type(count) is not int or not 1 <= count <= 99:
            return "invalid"
        cost = 0 if self.sandbox else item.buy_price * count
        result = self.ledger.apply(transaction, "buy:" + name, -cost, {name: count})
        return "insufficient_coins" if result == "insufficient" else result

    def sell_item(self, name: str, count: int, transaction: str) -> str:
        """Sell goods from storage; reserved materials cannot be sold."""
        item = self.catalog.items.get(name)
        if item is None or not item.sell_price:
            return "not_for_sale"
        if type(count) is not int or not 1 <= count <= 999:
            return "invalid"
        result = self.ledger.apply(transaction, "sell:" + name, item.sell_price * count, {name: -count})
        return "none_stored" if result == "insufficient" else result

    def free_cell(self, definition: str, zone: str) -> int | None:
        """The leftmost cell where the piece fits, preferring one free cell of space on each side.

        None when the zone has no room. Pieces packed edge to edge leave the residents no
        floor between them, so a spaced spot wins whenever there is one.
        """
        found = self.catalog.furniture.get(definition)
        if found is None or zone not in self.zones:
            return None
        width = self.zones[zone].width_cells
        taken = {cell for piece, other in self.in_zone(zone) for cell in range(piece.cell, piece.cell + other.width)}
        fitting = [cell for cell in range(max(0, width - found.width + 1)) if self.preview(definition, zone, cell) is None]
        spaced = [cell for cell in fitting if cell - 1 not in taken and cell + found.width not in taken]
        return (spaced or fitting or [None])[0]

    def place_anywhere(self, definition: str, zone: str) -> tuple[str, str | None]:
        """Put one stored piece in the first free spot, so buying never needs a position."""
        cell = self.free_cell(definition, zone)
        if cell is None:
            return ("unknown", None) if definition not in self.catalog.furniture else ("no_room", None)
        return self.place(definition, zone, cell)

    def furnish(self, zone: str) -> int:
        """Set out the starter kit's pieces wherever they fit; returns how many were placed."""
        placed = 0
        for item in STARTER_KIT:
            definition = item.removeprefix("furniture:")
            while self.stored(definition) and self.place_anywhere(definition, zone)[0] == "accepted":
                placed += 1
        return placed

    def buy_and_place(self, definition: str, zone: str | None, transaction: str) -> str:
        """Buy a piece and put it straight into the home; it stays in storage only when there is no room."""
        result = self.buy(definition, transaction)
        if result == "accepted" and zone is not None and not self.sandbox:
            if self.place_anywhere(definition, zone)[0] != "accepted":
                return "bought_no_room"
        return result

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

    @staticmethod
    def pair(first: str, second: str) -> str:
        return "|".join(sorted((first, second)))

    def relation(self, first: str, second: str) -> int:
        return self.relations.get(self.pair(first, second), 0)

    def adjust_relation(self, first: str, second: str, delta: int) -> int:
        key = self.pair(first, second)
        value = max(-RELATION_LIMIT, min(RELATION_LIMIT, self.relations.get(key, 0) + delta))
        if value:
            self.relations[key] = value
        else:
            self.relations.pop(key, None)
        return value

    def set_theme(self, zone: str, theme: str) -> str:
        """Change how a zone looks; furniture, paths and storage stay exactly as they are."""
        if zone not in self.zones or theme not in THEMES:
            return "unknown"
        self.zones[zone].theme = theme
        self.emit("theme_set", zone=zone, theme=theme)
        return "accepted"

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
        leaving = [task.identifier for task in self.tasks.values() if task.resident == identifier]
        for task in leaving:          # cancel_task removes entries, so collect first
            self.cancel_task(task)
        cancel_activity(self, resident, "left_home")
        for piece in self.furniture.values():
            if piece.owner == identifier:
                piece.owner = None
        for key in [key for key in self.relations if identifier in key.split("|")]:
            del self.relations[key]
        self.progress.wishes.pop(identifier, None)
        self.progress.arrivals.pop(identifier, None)
        del self.residents[identifier]
        return "accepted"

    def station_level(self, definition: str) -> int:
        """Every station of a kind shares its level, so storing or rearranging never loses one."""
        return self.progress.upgrades.get(definition, 1)

    def upgrade_cost(self, definition: str) -> int | None:
        """Coins for the next level of a workstation kind; None when it cannot go higher."""
        found = self.catalog.furniture.get(definition)
        if found is None or found.profession is None or self.station_level(definition) >= MAX_STATION_LEVEL:
            return None
        return 0 if self.sandbox else max(found.price, UPGRADE_BASE_COINS) * self.station_level(definition)

    def upgrade(self, definition: str, transaction: str) -> str:
        cost = self.upgrade_cost(definition)
        if cost is None:
            return "not_upgradable"
        if cost:
            result = self.ledger.apply(transaction, "upgrade:" + definition, -cost)
            if result != "accepted":
                return "insufficient_coins" if result == "insufficient" else result
        self.progress.upgrades[definition] = self.station_level(definition) + 1
        self.emit("upgraded", definition=definition, level=self.progress.upgrades[definition])
        return "accepted"

    def interact(self, identifier: str, kind: str) -> str:
        """Feed, pat or talk to a pet; it never interrupts what the pet is doing."""
        resident = self.residents.get(identifier)
        if resident is None or kind not in INTERACTIONS:
            return "unknown"
        if resident.parked or resident.away:
            return "parked"
        last = self._interacted.get((identifier, kind))
        if last is not None and self.time_ms - last < INTERACT_COOLDOWN_MS:
            return "too_soon"
        self._interacted[(identifier, kind)] = self.time_ms
        for need, change in INTERACTIONS[kind].items():
            resident.needs[need] = max(0, min(100, resident.needs[need] + change))
        if kind == "pat":
            resident.affection = min(MAX_AFFECTION, resident.affection + 1)
        self.emit("interacted", resident=identifier, interaction=kind)
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
        self.emit("routine_set", resident=identifier, routine=routine)
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
        if not unlocked(self, found.unlock_level):
            return "locked", None
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
