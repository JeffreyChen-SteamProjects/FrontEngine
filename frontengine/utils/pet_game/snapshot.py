"""Versioned home snapshots: the only path between a World and saved JSON.

Loading validates every field and every cross-reference before a World exists.
Furniture or work whose definition is not installed (a removed content pack) is
kept verbatim as dormant data and written back unchanged, so reinstalling the
content restores the original layout instead of losing it.
"""
from __future__ import annotations

import json
import re

from frontengine.utils.pet_game.catalog import Catalog
from frontengine.utils.pet_game.goals import Progress
from frontengine.utils.pet_game.jobs import MAX_TASKS, Task
from frontengine.utils.pet_game.layout import MAX_FURNITURE, Furniture, Zone, checked_int, placement_problem
from frontengine.utils.pet_game.ledger import Ledger
from frontengine.utils.pet_game.resident import Resident
from frontengine.utils.pet_game.world import (
    FORMAT, MAX_RESIDENTS, MAX_ZONES, MODES, VERSION, World, furniture_item,
)

FIELDS_V1 = {"format", "version", "home", "mode", "time_ms", "rng", "next_id", "zones", "furniture",
             "residents", "tasks", "ledger", "flags", "dormant"}
FIELDS_V2 = FIELDS_V1 | {"relations"}
FIELDS = FIELDS_V2 | {"progress"}
FIELDS_BY_VERSION = {1: FIELDS_V1, 2: FIELDS_V2, 3: FIELDS, 4: FIELDS}     # 4 changed zones only
_PAIR = re.compile(r"[0-9a-f]{32}\|[0-9a-f]{32}")
MAX_TIME_MS = 10 ** 13
MAX_DORMANT = 200
_FLAGS = 64


class NewerSaveError(ValueError):
    """The save was written by a newer FrontEngine; never overwrite it."""


def to_dict(world: World) -> dict:
    return {
        "format": FORMAT, "version": VERSION, "home": world.home, "mode": world.mode,
        "time_ms": world.time_ms, "rng": world.rng.state, "next_id": world.next_id,
        "zones": [zone.to_dict() for zone in world.zones.values()],
        "furniture": [piece.to_dict() for piece in world.furniture.values()],
        "residents": [resident.to_dict() for resident in world.residents.values()],
        "tasks": [_saved_task(task) for task in world.tasks.values()],
        "ledger": world.ledger.to_dict(), "flags": sorted(world.flags),
        "dormant": [dict(item) for item in world.dormant],
        "relations": dict(sorted(world.relations.items())),
        "progress": world.progress.to_dict(),
    }


def _saved_task(task: Task) -> dict:
    """Nobody is walking or working after a reload, so the save says paused."""
    data = task.to_dict()
    if data["state"] in ("travelling", "working"):
        data["state"] = "paused"
    return data


def check_header(data: object) -> None:
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise ValueError("Not a FrontEngine home save")
    version = data.get("version")
    if type(version) is not int or version < 1:
        raise ValueError("Invalid home save version")
    if version > VERSION:
        raise NewerSaveError(f"Home save version {version} is newer than supported {VERSION}")
    if set(data) != FIELDS_BY_VERSION[version]:
        raise ValueError("Invalid home save fields")


def _list(data: dict, key: str, limit: int) -> list:
    value = data[key]
    if not isinstance(value, list) or len(value) > limit:
        raise ValueError(f"Invalid {key} list")
    return value


def _unique(items: list, label: str) -> dict:
    found = {}
    for item in items:
        if item.identifier in found:
            raise ValueError(f"Duplicate {label} identity")
        found[item.identifier] = item
    return found


_DORMANT_FIELD = {"furniture": "definition", "task": "recipe"}


def _known(catalog: Catalog, kind: str) -> dict:
    return catalog.furniture if kind == "furniture" else catalog.recipes


def _dormant(raw: object, kind: str, catalog: Catalog) -> bool:
    """A well-shaped record whose content is missing is kept; anything else is rejected."""
    field = _DORMANT_FIELD[kind]
    return (isinstance(raw, dict) and len(raw) <= 16 and isinstance(raw.get(field), str)
            and len(raw[field]) <= 48 and raw[field] not in _known(catalog, kind)
            and len(json.dumps(raw, allow_nan=False)) <= 4096)


def _split(raw_items: list, catalog: Catalog, kind: str) -> tuple[list, list]:
    live, dormant = [], []
    field = _DORMANT_FIELD[kind]
    for raw in raw_items:
        if isinstance(raw, dict) and raw.get(field) in _known(catalog, kind):
            live.append(raw)
        elif _dormant(raw, kind, catalog):
            dormant.append({"kind": kind, "record": raw})
        else:
            raise ValueError(f"Invalid {kind} record")
    return live, dormant


def from_dict(data: object, catalog: Catalog) -> World:
    check_header(data)
    if not isinstance(data, dict):        # check_header already ensured this; keeps the type explicit
        raise ValueError("Not a FrontEngine home save")
    if data["mode"] not in MODES:
        raise ValueError("Invalid home mode")
    world = World(catalog, data["home"], data["mode"], data["rng"])
    world.time_ms = checked_int(data["time_ms"], 0, MAX_TIME_MS, "home time")
    world.next_id = checked_int(data["next_id"], 1, 999_999_999, "identity counter")
    raw_zones = _list(data, "zones", MAX_ZONES)
    if data["version"] < 4:              # zones gained floor areas in version 4
        raw_zones = [{**raw, "areas": []} if isinstance(raw, dict) and "areas" not in raw else raw
                     for raw in raw_zones]
    world.zones = _unique([Zone.from_dict(raw) for raw in raw_zones], "zone")
    revived = _saved_dormant(_list(data, "dormant", MAX_DORMANT))
    pieces, dormant_pieces = _split(_list(data, "furniture", MAX_FURNITURE) + revived["furniture"],
                                    catalog, "furniture")
    tasks, dormant_tasks = _split(_list(data, "tasks", MAX_TASKS) + revived["task"], catalog, "task")
    if len(pieces) > MAX_FURNITURE or len(tasks) > MAX_TASKS:
        raise ValueError("Too many records after restoring installed content")
    world.furniture = _unique([Furniture.from_dict(raw, catalog) for raw in pieces], "furniture")
    world.residents = _unique([Resident.from_dict(raw) for raw in _list(data, "residents", MAX_RESIDENTS)],
                              "resident")
    world.tasks = _unique([Task.from_dict(raw, catalog) for raw in tasks], "task")
    world.ledger = Ledger.from_dict(data["ledger"])
    flags = _list(data, "flags", _FLAGS)
    if any(not isinstance(flag, str) or not 0 < len(flag) <= 48 for flag in flags):
        raise ValueError("Invalid home flags")
    world.flags = set(flags)
    world.dormant = dormant_pieces + dormant_tasks
    if len(world.dormant) > MAX_DORMANT:
        raise ValueError("Too many unavailable records")
    world.relations = _checked_relations(data.get("relations", {}), world)
    world.progress = Progress.from_dict(data["progress"]) if "progress" in data else Progress()
    for identifier in world.residents:              # homes saved before version 3 start counting now
        world.progress.arrivals.setdefault(identifier, world.time_ms)
    world.progress.arrivals = {key: value for key, value in world.progress.arrivals.items()
                               if key in world.residents}
    world.progress.wishes = {key: value for key, value in world.progress.wishes.items()
                             if key in world.residents}
    _check_references(world)
    return world


def _checked_relations(value: object, world: World) -> dict[str, int]:
    """Pairs of residents still living here; anything malformed rejects the save."""
    if not isinstance(value, dict) or len(value) > 200:
        raise ValueError("Invalid relationships")
    relations = {}
    for key, amount in value.items():
        if not isinstance(key, str) or not _PAIR.fullmatch(key) or key != world.pair(*key.split("|")):
            raise ValueError("Invalid relationship pair")
        relations[key] = checked_int(amount, -100, 100, "relationship")
    return {key: amount for key, amount in relations.items()
            if all(member in world.residents for member in key.split("|"))}


def _saved_dormant(items: list) -> dict[str, list]:
    """Unwrap saved unavailable records; ones whose content is back become live again."""
    records: dict[str, list] = {kind: [] for kind in _DORMANT_FIELD}
    for item in items:
        if (not isinstance(item, dict) or set(item) != {"kind", "record"}
                or item["kind"] not in _DORMANT_FIELD or not isinstance(item["record"], dict)):
            raise ValueError("Invalid unavailable record")
        records[item["kind"]].append(item["record"])
    return records


def _check_references(world: World) -> None:
    """Every ID a record points at must exist; identities must stay below the counter."""
    for collection in (world.zones, world.furniture, world.tasks):
        if any(int(identifier[1:]) >= world.next_id for identifier in collection):
            raise ValueError("Identity is ahead of the counter")
    _check_placements(world)
    _check_tasks(world)
    _recover_overlaps(world)


def _check_placements(world: World) -> None:
    for resident in world.residents.values():
        if resident.zone not in world.zones:
            raise ValueError("Resident lives in an unknown zone")
        width = world.zones[resident.zone].width_pixels * 1000
        resident.x_milli = min(resident.x_milli, width - 1)
    for piece in world.furniture.values():
        if piece.zone not in world.zones:
            raise ValueError("Furniture stands in an unknown zone")
        if piece.owner is not None and piece.owner not in world.residents:
            piece.owner = None


def _check_tasks(world: World) -> None:
    for task in world.tasks.values():
        if task.resident not in world.residents:
            raise ValueError("Task belongs to an unknown resident")
        if task.station is not None and task.station not in world.furniture:
            task.station = None


def _recover_overlaps(world: World) -> None:
    """A layout that no longer fits (changed footprints) returns later pieces to storage."""
    accepted: dict[str, list] = {}
    for identifier in sorted(world.furniture, key=lambda key: int(key[1:])):
        piece = world.furniture[identifier]
        definition = world.definition(piece)
        others = accepted.setdefault(piece.zone, [])
        if placement_problem(world.zones[piece.zone], definition, piece.cell, others) is None:
            others.append((piece, definition))
            continue
        if not world.sandbox:
            world.ledger.apply("recover:" + identifier, "recover",
                               items={furniture_item(piece.definition): 1})
        for task in world.tasks.values():
            if task.station == identifier:
                task.station = None
        del world.furniture[identifier]
