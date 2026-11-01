"""Home zones, placed furniture, placement checks and interaction reservations.

A zone is a strip of floor along a screen edge, measured in grid cells in that
screen's logical coordinates. Residents walk in front of furniture, so the
floor stays connected; what placement can break is the footprint (outside the
zone, overlapping another solid piece, covering a restricted cell) and the
entrance, which must stay clear so residents can arrive and leave.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from frontengine.utils.pet_game.catalog import CELL_PIXELS, Catalog, FurnitureDefinition

THEMES = ("warm_home", "green_studio", "night_studio")
# Area labels on a zone's floor: they steer which piece a resident picks, never forbid one.
AREA_TAGS = ("living", "work", "leisure", "dining")
AREA_FOR_ACTIVITY = {"sleep": "living", "eat": "dining", "work": "work", "play": "leisure", "relax": "leisure"}
MAX_AREAS = 16
CLIMBING_TRAITS = ("playful",)       # pets with one of these jump onto raised pieces by themselves
MIN_ZONE_CELLS = 8
MAX_ZONE_CELLS = 160
MAX_FURNITURE = 400
_LOCAL_ID = re.compile(r"[a-z]\d{1,9}")
RESIDENT_ID = re.compile(r"[0-9a-f]{32}")


def check_local_id(value: object, prefix: str) -> str:
    if not isinstance(value, str) or not _LOCAL_ID.fullmatch(value) or value[0] != prefix:
        raise ValueError(f"Invalid {prefix} identity: {value!r}")
    return value


def checked_int(value: object, low: int, high: int, label: str) -> int:
    """An exact int (never bool or float) inside the inclusive range."""
    if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high:
        return value
    raise ValueError(f"Invalid {label}")


_int = checked_int


@dataclass
class Zone:
    """One home area on one screen; coordinates are local logical pixels."""

    identifier: str
    screen: str
    x: int
    y: int
    width_cells: int
    theme: str = "warm_home"
    entrance: int = 0
    restricted: tuple[int, ...] = ()
    areas: tuple[tuple[int, int, str], ...] = ()      # (first cell, last cell, tag), sorted, apart
    link: str | None = None          # the zone its entrance leads to, a crossing point between screens

    def area_at(self, cell: int) -> str | None:
        return next((tag for first, last, tag in self.areas if first <= cell <= last), None)

    def with_area(self, first: int, last: int, tag: str | None) -> tuple[tuple[int, int, str], ...]:
        """The areas after labelling ``first..last`` (``None`` clears it); neighbours are trimmed."""
        first, last = max(0, min(first, last)), min(self.width_cells - 1, max(first, last))
        kept = []
        for start, end, old in self.areas:
            if end < first or start > last:
                kept.append((start, end, old))
                continue
            if start < first:
                kept.append((start, first - 1, old))
            if end > last:
                kept.append((last + 1, end, old))
        if tag is not None:
            kept.append((first, last, tag))
        return tuple(sorted(kept))[:MAX_AREAS]

    @property
    def width_pixels(self) -> int:
        return self.width_cells * CELL_PIXELS

    def to_dict(self) -> dict:
        return {"id": self.identifier, "screen": self.screen, "x": self.x, "y": self.y,
                "width_cells": self.width_cells, "theme": self.theme,
                "entrance": self.entrance, "restricted": list(self.restricted),
                "areas": [list(area) for area in self.areas], "link": self.link}

    @classmethod
    def from_dict(cls, data: object) -> Zone:
        keys = {"id", "screen", "x", "y", "width_cells", "theme", "entrance", "restricted", "areas", "link"}
        if not isinstance(data, dict) or set(data) != keys:
            raise ValueError("Invalid zone fields")
        if not isinstance(data["screen"], str) or len(data["screen"]) > 128:
            raise ValueError("Invalid zone screen")
        if data["theme"] not in THEMES:
            raise ValueError("Unknown zone theme")
        width = _int(data["width_cells"], MIN_ZONE_CELLS, MAX_ZONE_CELLS, "zone width")
        restricted = data["restricted"]
        if not isinstance(restricted, list) or len(restricted) > width:
            raise ValueError("Invalid restricted cells")
        return cls(check_local_id(data["id"], "z"), data["screen"],
                   _int(data["x"], -100000, 100000, "zone x"), _int(data["y"], -100000, 100000, "zone y"),
                   width, data["theme"], _int(data["entrance"], 0, width - 1, "zone entrance"),
                   tuple(sorted({_int(cell, 0, width - 1, "restricted cell") for cell in restricted})),
                   _checked_areas(data["areas"], width),
                   None if data["link"] is None else check_local_id(data["link"], "z"))


def _checked_areas(value: object, width: int) -> tuple[tuple[int, int, str], ...]:
    if not isinstance(value, list) or len(value) > MAX_AREAS:
        raise ValueError("Invalid zone areas")
    areas = []
    for entry in value:
        if not isinstance(entry, list) or len(entry) != 3 or entry[2] not in AREA_TAGS:
            raise ValueError("Invalid zone area")
        first, last = _int(entry[0], 0, width - 1, "area start"), _int(entry[1], 0, width - 1, "area end")
        if last < first:
            raise ValueError("Invalid zone area")
        areas.append((first, last, entry[2]))
    areas.sort()
    if any(previous[1] >= current[0] for previous, current in zip(areas, areas[1:])):
        raise ValueError("Overlapping zone areas")
    return tuple(areas)


@dataclass
class Furniture:
    """A placed instance. ``users`` maps interaction point index to a resident (runtime only)."""

    identifier: str
    definition: str
    zone: str
    cell: int
    flipped: bool = False
    owner: str | None = None
    users: dict[int, str] = field(default_factory=dict)

    def cells(self, definition: FurnitureDefinition) -> range:
        return range(self.cell, self.cell + definition.width)

    def point_cell(self, definition: FurnitureDefinition, index: int) -> int:
        offset = definition.points[index]
        if self.flipped:
            offset = definition.width - 1 - offset
        return self.cell + offset

    def point_x_milli(self, definition: FurnitureDefinition, index: int) -> int:
        """Centre of the interaction cell in milli-pixels, local to the zone."""
        return (self.point_cell(definition, index) * CELL_PIXELS + CELL_PIXELS // 2) * 1000

    def free_point(self, definition: FurnitureDefinition) -> int | None:
        for index in range(len(definition.points)):
            if index not in self.users:
                return index
        return None

    def to_dict(self) -> dict:
        return {"id": self.identifier, "definition": self.definition, "zone": self.zone,
                "cell": self.cell, "flipped": self.flipped, "owner": self.owner}

    @classmethod
    def from_dict(cls, data: object, catalog: Catalog) -> Furniture:
        if not isinstance(data, dict) or set(data) != {"id", "definition", "zone", "cell", "flipped", "owner"}:
            raise ValueError("Invalid furniture fields")
        if data["definition"] not in catalog.furniture:
            raise ValueError("Unknown furniture definition")
        if type(data["flipped"]) is not bool:
            raise ValueError("Invalid furniture orientation")
        owner = data["owner"]
        if owner is not None and (not isinstance(owner, str) or not RESIDENT_ID.fullmatch(owner)):
            raise ValueError("Invalid furniture owner")
        return cls(check_local_id(data["id"], "f"), data["definition"], check_local_id(data["zone"], "z"),
                   _int(data["cell"], 0, MAX_ZONE_CELLS - 1, "furniture cell"), data["flipped"], owner)


def has_steps(piece: Furniture, definition: FurnitureDefinition,
              others: list[tuple[Furniture, FurnitureDefinition]]) -> bool:
    """Pet stairs touching or overlapping the piece's footprint (one cell either side counts)."""
    first, last = piece.cell - 1, piece.cell + definition.width
    return any(other_definition.steps and other.cell <= last and other.cell + other_definition.width - 1 >= first
               for other, other_definition in others if other is not piece)


def can_climb(traits) -> bool:
    return any(trait in CLIMBING_TRAITS for trait in traits)


def placement_problem(zone: Zone, definition: FurnitureDefinition, cell: int,
                      others: list[tuple[Furniture, FurnitureDefinition]]) -> str | None:
    """Return why a footprint cannot go here, or None when it fits.

    ``others`` are the pieces already in the zone, excluding the one being moved.
    """
    if type(cell) is not int or cell < 0 or cell + definition.width > zone.width_cells:
        return "outside_zone"
    footprint = set(range(cell, cell + definition.width))
    if footprint & set(zone.restricted):
        return "restricted"
    if definition.solid and zone.entrance in footprint:
        return "entrance_blocked"
    if definition.solid:
        for other, other_definition in others:
            if other_definition.solid and footprint & set(other.cells(other_definition)):
                return "overlap"
    return None
