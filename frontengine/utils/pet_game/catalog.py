"""Furniture and recipe definitions: tunable data, validated before any world uses it.

Rates are integer points per effective minute so simulation stays exact and
replayable. Prices are whole home coins; nothing in the economy is a float.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

CELL_PIXELS = 32          # one layout grid cell in logical pixels
NEEDS = ("energy", "fullness", "mood")
ACTIVITIES = ("sleep", "eat", "work", "play", "relax")
CATEGORIES = ("bed", "table", "workstation", "leisure", "decoration")
PROFESSIONS = ("writing", "crafting", "gardening")
_IDENTIFIER = re.compile(r"[a-z][a-z0-9_]{0,47}")
MAX_WIDTH_CELLS = 16
MAX_POINTS = 6


@dataclass(frozen=True)
class FurnitureDefinition:
    """What a piece of furniture is; placement and use are in the world."""

    identifier: str
    label_key: str
    fallback: str
    category: str
    width: int                       # footprint in grid cells
    solid: bool                      # solid pieces cannot overlap other solid pieces
    points: tuple[int, ...] = ()     # interaction cell offsets, one user each
    activity: str | None = None
    effects: dict[str, int] = field(default_factory=dict)   # need -> points/minute
    price: int = 0
    sell_back: int = 0
    essential: bool = False          # basic facilities are never sold
    comfort: int = 0                 # home comfort while placed
    profession: str | None = None
    use_ms: tuple[int, int] = (0, 0)  # leisure duration range


@dataclass(frozen=True)
class Recipe:
    """One unit of work at a station; rewards exist only after completion."""

    identifier: str
    label_key: str
    fallback: str
    profession: str
    duration_ms: int
    energy_per_minute: int
    coins: int
    experience: int
    inputs: dict[str, int] = field(default_factory=dict)
    outputs: dict[str, int] = field(default_factory=dict)
    min_level: int = 1


def _check_identifier(value: object) -> None:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"Invalid catalog identifier: {value!r}")


def _check_counts(values: dict, label: str) -> None:
    for key, amount in values.items():
        _check_identifier(key)
        if type(amount) is not int or not 0 < amount <= 999:
            raise ValueError(f"Invalid {label} amount for {key}")


def _is_int(value: object, low: int, high: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high


def _check_footprint(definition: FurnitureDefinition) -> None:
    if not _is_int(definition.width, 1, MAX_WIDTH_CELLS):
        raise ValueError("Furniture width out of range")
    if len(definition.points) > MAX_POINTS or len(set(definition.points)) != len(definition.points):
        raise ValueError("Invalid interaction points")
    if not all(_is_int(point, 0, definition.width - 1) for point in definition.points):
        raise ValueError("Interaction point outside the footprint")


def check_furniture(definition: FurnitureDefinition) -> None:
    """Reject definitions the simulation could not honour."""
    _check_identifier(definition.identifier)
    if definition.category not in CATEGORIES:
        raise ValueError("Unknown furniture category")
    _check_footprint(definition)
    if (definition.activity is None) != (not definition.points):
        raise ValueError("Furniture with an activity needs interaction points")
    if definition.activity is not None and definition.activity not in ACTIVITIES:
        raise ValueError("Unknown furniture activity")
    if set(definition.effects) - set(NEEDS) or not all(
            _is_int(rate, -600, 600) for rate in definition.effects.values()):
        raise ValueError("Invalid furniture effects")
    if not 0 <= definition.sell_back <= definition.price // 2 or definition.price > 100000:
        raise ValueError("Sell-back must not exceed half the price")
    if (definition.category == "workstation") != (definition.profession in PROFESSIONS):
        raise ValueError("Workstations need exactly one known profession")
    low, high = definition.use_ms
    if not 0 <= low <= high <= 3600000:
        raise ValueError("Invalid use duration")


def check_recipe(recipe: Recipe) -> None:
    _check_identifier(recipe.identifier)
    if recipe.profession not in PROFESSIONS:
        raise ValueError("Unknown recipe profession")
    if type(recipe.duration_ms) is not int or not 1000 <= recipe.duration_ms <= 3600000:
        raise ValueError("Recipe duration out of range")
    for value in (recipe.energy_per_minute, recipe.coins, recipe.experience, recipe.min_level):
        if type(value) is not int or not 0 <= value <= 100000:
            raise ValueError("Recipe values must be nonnegative integers")
    _check_counts(recipe.inputs, "input")
    _check_counts(recipe.outputs, "output")


class Catalog:
    """Immutable lookup of validated furniture and recipes with unique identities."""

    def __init__(self, furniture: list[FurnitureDefinition], recipes: list[Recipe]) -> None:
        self.furniture: dict[str, FurnitureDefinition] = {}
        self.recipes: dict[str, Recipe] = {}
        for definition in furniture:
            check_furniture(definition)
            if definition.identifier in self.furniture:
                raise ValueError("Duplicate furniture identity")
            self.furniture[definition.identifier] = definition
        for recipe in recipes:
            check_recipe(recipe)
            if recipe.identifier in self.recipes:
                raise ValueError("Duplicate recipe identity")
            self.recipes[recipe.identifier] = recipe

    def recipes_for(self, profession: str) -> list[Recipe]:
        return [recipe for recipe in self.recipes.values() if recipe.profession == profession]


def _furniture() -> list[FurnitureDefinition]:
    return [
        FurnitureDefinition("bed_basic", "pet_game_bed_basic", "Simple bed", "bed", 4, True, (1,),
                            "sleep", {"energy": 30}, essential=True),
        FurnitureDefinition("table_basic", "pet_game_table_basic", "Dining table", "table", 4, True,
                            (0, 3), "eat", {"fullness": 60}, essential=True),
        FurnitureDefinition("desk_basic", "pet_game_desk_basic", "Writing desk", "workstation", 3, True,
                            (1,), "work", essential=True, profession="writing"),
        FurnitureDefinition("plant_pot", "pet_game_plant_pot", "Potted plant", "decoration", 1, False,
                            price=15, sell_back=7, comfort=2),
        FurnitureDefinition("toy_box", "pet_game_toy_box", "Toy box", "leisure", 2, True, (0,), "play",
                            {"mood": 20, "energy": -4}, price=40, sell_back=20, use_ms=(30000, 45000)),
        FurnitureDefinition("armchair", "pet_game_armchair", "Armchair", "leisure", 2, True, (0,), "relax",
                            {"mood": 10, "energy": 6}, price=60, sell_back=30, comfort=1,
                            use_ms=(40000, 60000)),
        FurnitureDefinition("bed_cozy", "pet_game_bed_cozy", "Cozy bed", "bed", 4, True, (1,), "sleep",
                            {"energy": 45, "mood": 2}, price=120, sell_back=60, comfort=2),
        FurnitureDefinition("wall_lamp", "pet_game_wall_lamp", "Wall lamp", "decoration", 1, False,
                            price=25, sell_back=12, comfort=3),
    ]


def _recipes() -> list[Recipe]:
    return [
        Recipe("letter", "pet_game_recipe_letter", "Write a letter", "writing", 120000, 6, 12, 5),
        Recipe("story", "pet_game_recipe_story", "Write a short story", "writing", 300000, 8, 36, 14,
               min_level=2),
    ]


def builtin_catalog() -> Catalog:
    """The playable built-in content; content packs extend this through the same checks."""
    return Catalog(_furniture(), _recipes())


STARTER_KIT = {"furniture:bed_basic": 1, "furniture:table_basic": 1, "furniture:desk_basic": 1}
STARTER_COINS = 10
