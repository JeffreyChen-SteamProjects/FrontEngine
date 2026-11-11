"""Home blueprints: a whole home's rooms and furniture as a file to share, and a read-only visit.

A blueprint carries only what the home looks like - each zone's width, theme, entrance,
restricted cells and floor areas, and every piece's kind, cell and mirroring. It never
holds pets, names, coins, goals, screen names or any identity, so sharing one shares
nothing about its owner. Visiting builds a throwaway free-arranging world that nothing
runs or saves; pieces this FrontEngine does not know are counted as missing, not trusted.
"""
from __future__ import annotations

import json
import uuid
from collections import Counter

from frontengine.utils.pet_game.arrangement import _stairs_first
from frontengine.utils.pet_game.catalog import _check_identifier as check_identifier
from frontengine.utils.pet_game.layout import MAX_FURNITURE, MAX_ZONE_CELLS, MIN_ZONE_CELLS, Zone, known_theme

BLUEPRINT_FORMAT = "frontengine.home-blueprint"
BLUEPRINT_VERSION = 1
MAX_BLUEPRINT_BYTES = 128 * 1024
MAX_BLUEPRINT_ZONES = 8
_ZONE_FIELDS = {"width_cells", "theme", "entrance", "restricted", "areas"}


def export_blueprint(world) -> str:
    """The home's look as JSON text; zones in their saved order, nothing personal."""
    order = list(world.zones)
    zones = []
    for key in order:
        zone = world.zones[key]
        zones.append({"width_cells": zone.width_cells, "theme": zone.theme, "entrance": zone.entrance,
                      "restricted": list(zone.restricted), "areas": [list(area) for area in zone.areas]})
    pieces = sorted([order.index(piece.zone), piece.definition, piece.cell, piece.flipped]
                    for piece in world.furniture.values() if piece.zone in world.zones)
    return json.dumps({"format": BLUEPRINT_FORMAT, "version": BLUEPRINT_VERSION, "zones": zones,
                       "pieces": pieces}, separators=(",", ":"))


def _int(value: object, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValueError("Invalid blueprint number")
    return value


def _zone(raw: object, index: int) -> Zone:
    if not isinstance(raw, dict) or set(raw) != _ZONE_FIELDS:
        raise ValueError("Invalid blueprint zone")
    if not known_theme(raw["theme"]):
        raise ValueError("Unknown blueprint theme")
    width = _int(raw["width_cells"], MIN_ZONE_CELLS, MAX_ZONE_CELLS)
    # Rebuilt through Zone.from_dict, so restricted cells and areas get the save file's own checks.
    return Zone.from_dict({"id": f"z{index + 1}", "screen": f"blueprint-{index + 1}", "x": 0, "y": 0,
                           "width_cells": width, "theme": raw["theme"], "entrance": raw["entrance"],
                           "restricted": raw["restricted"], "areas": raw["areas"], "link": None})


def parse_blueprint(text: object) -> tuple[list[Zone], list[tuple[int, str, int, bool]]]:
    """Validate a blueprint at the boundary; anything unexpected is rejected, never trusted."""
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_BLUEPRINT_BYTES:
        raise ValueError("Blueprint too large")
    data = json.loads(text)
    if (not isinstance(data, dict) or set(data) != {"format", "version", "zones", "pieces"}
            or data["format"] != BLUEPRINT_FORMAT or data["version"] != BLUEPRINT_VERSION):
        raise ValueError("Not a FrontEngine home blueprint")
    raw_zones, raw_pieces = data["zones"], data["pieces"]
    if not isinstance(raw_zones, list) or not 1 <= len(raw_zones) <= MAX_BLUEPRINT_ZONES:
        raise ValueError("Invalid blueprint zones")
    if not isinstance(raw_pieces, list) or len(raw_pieces) > MAX_FURNITURE:
        raise ValueError("Invalid blueprint pieces")
    zones = [_zone(raw, index) for index, raw in enumerate(raw_zones)]
    pieces = []
    for entry in raw_pieces:
        if not isinstance(entry, list) or len(entry) != 4 or type(entry[3]) is not bool:
            raise ValueError("Invalid blueprint piece")
        check_identifier(entry[1])            # a catalog-style name, never a path or anything else
        zone = _int(entry[0], 0, len(zones) - 1)
        pieces.append((zone, entry[1], _int(entry[2], 0, MAX_ZONE_CELLS - 1), entry[3]))
    return zones, pieces


def canonical_blueprint(text: str) -> str:
    """The blueprint rewritten from its checked parts only - what is shared on the Workshop."""
    zones, pieces = parse_blueprint(text)
    return json.dumps({"format": BLUEPRINT_FORMAT, "version": BLUEPRINT_VERSION,
                       "zones": [{"width_cells": zone.width_cells, "theme": zone.theme, "entrance": zone.entrance,
                                  "restricted": list(zone.restricted), "areas": [list(a) for a in zone.areas]}
                                 for zone in zones],
                       "pieces": sorted([list(piece) for piece in pieces])}, separators=(",", ":"))


def required_packs(text: str) -> list[str]:
    """The content packs a blueprint's pieces and themes come from (``<pack>__<id>``), sorted."""
    zones, pieces = parse_blueprint(text)
    names = [name for _zone, name, _cell, _flipped in pieces] + [zone.theme for zone in zones]
    return sorted({name.split("__", 1)[0] for name in names if "__" in name})


def visit_blueprint(text: str, catalog):
    """A throwaway world to look at: ``(world, missing)`` counting pieces it cannot show here -
    unknown to this FrontEngine (from newer content or a content pack) or not placeable.

    The world is in free-arranging mode so nothing is bought or stored; it is never saved or run.
    """
    from frontengine.utils.pet_game.world import World
    zones, pieces = parse_blueprint(text)
    world = World(catalog, uuid.uuid4().hex, "sandbox", seed=1)
    world.zones = {zone.identifier: zone for zone in zones}
    missing: Counter = Counter()
    known = [(z, name, cell, flipped) for z, name, cell, flipped in pieces if name in catalog.furniture]
    missing.update(name for _z, name, _cell, _flipped in pieces if name not in catalog.furniture)
    for index in _stairs_first(world, (name for _z, name, _cell, _flipped in known)):
        zone, name, cell, flipped = known[index]
        if world.place(name, zones[zone].identifier, cell, flipped)[0] != "accepted":
            missing[name] += 1
    return world, dict(missing)

