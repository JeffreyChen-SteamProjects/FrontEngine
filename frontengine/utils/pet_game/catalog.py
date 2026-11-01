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
ITEM_KINDS = ("material", "food", "goods")
FURNITURE_PREFIX = "furniture:"
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
    phases: tuple[str, ...] = ("work",)      # equal shares of the duration, shown to the player

    def phase_at(self, progress_ms: int) -> str:
        index = min(len(self.phases) - 1, progress_ms * len(self.phases) // self.duration_ms)
        return self.phases[index]


@dataclass(frozen=True)
class ItemDefinition:
    """A stackable thing in storage. buy_price 0 means the shop does not sell it."""

    identifier: str
    label_key: str
    fallback: str
    kind: str
    buy_price: int = 0
    sell_price: int = 0


def _check_identifier(value: object) -> None:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"Invalid catalog identifier: {value!r}")


def _check_counts(values: dict, label: str) -> None:
    for key, amount in values.items():
        _check_identifier(key.removeprefix(FURNITURE_PREFIX))
        if not _is_int(amount, 1, 999):
            raise ValueError(f"Invalid {label} amount for {key}")


def check_item(item: ItemDefinition) -> None:
    """Buying must always cost more than selling returns, so no buy-sell loop makes money."""
    _check_identifier(item.identifier)
    if item.kind not in ITEM_KINDS:
        raise ValueError("Unknown item kind")
    if not _is_int(item.sell_price, 0, 100000) or not _is_int(item.buy_price, 0, 100000):
        raise ValueError("Item prices must be whole coins")
    if item.buy_price and item.buy_price <= item.sell_price:
        raise ValueError("An item must not sell for as much as it costs")


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
    if not 1 <= len(recipe.phases) <= 4:
        raise ValueError("A recipe has one to four phases")
    for phase in recipe.phases:
        _check_identifier(phase)


class Catalog:
    """Immutable lookup of validated furniture and recipes with unique identities."""

    def __init__(self, furniture: list[FurnitureDefinition], recipes: list[Recipe],
                 items: list[ItemDefinition] | None = None) -> None:
        self.furniture: dict[str, FurnitureDefinition] = {}
        self.recipes: dict[str, Recipe] = {}
        self.items: dict[str, ItemDefinition] = {}
        for item in items or []:
            check_item(item)
            if item.identifier in self.items:
                raise ValueError("Duplicate item identity")
            self.items[item.identifier] = item
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
        for recipe in self.recipes.values():
            for name in (*recipe.inputs, *recipe.outputs):
                if not self.knows_item(name):
                    raise ValueError(f"Recipe {recipe.identifier} uses an unknown item {name}")
        self._reject_loops()

    def knows_item(self, name: str) -> bool:
        if name.startswith(FURNITURE_PREFIX):
            return name.removeprefix(FURNITURE_PREFIX) in self.furniture
        return name in self.items

    def sell_price(self, name: str) -> int:
        if name.startswith(FURNITURE_PREFIX):
            return self.furniture[name.removeprefix(FURNITURE_PREFIX)].sell_back
        return self.items[name].sell_price

    def _reject_loops(self) -> None:
        """No chain of recipes may turn an item back into itself (no endless conversion loop)."""
        edges: dict[str, set[str]] = {}
        for recipe in self.recipes.values():
            for source in recipe.inputs:
                edges.setdefault(source, set()).update(recipe.outputs)

        def reaches(start: str, goal: str, seen: set[str]) -> bool:
            for target in edges.get(start, ()):
                if target == goal or (target not in seen and reaches(target, goal, seen | {target})):
                    return True
            return False

        for item in edges:
            if reaches(item, item, {item}):
                raise ValueError(f"Recipes loop back to {item}")

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
        FurnitureDefinition("planter", "pet_game_planter", "Planter", "workstation", 2, True, (0,), "work",
                            price=150, sell_back=75, comfort=1, profession="gardening"),
        FurnitureDefinition("workbench", "pet_game_workbench", "Workbench", "workstation", 3, True, (1,), "work",
                            price=220, sell_back=110, profession="crafting"),
        FurnitureDefinition("stool", "pet_game_stool", "Wooden stool", "leisure", 1, True, (0,), "relax",
                            {"mood": 6, "energy": 4}, price=45, sell_back=20, use_ms=(30000, 45000)),
    ]


def _recipes() -> list[Recipe]:
    return [
        Recipe("letter", "pet_game_recipe_letter", "Write a letter", "writing", 120000, 6, 12, 5,
               phases=("draft", "write", "deliver")),
        Recipe("story", "pet_game_recipe_story", "Write a short story", "writing", 300000, 8, 36, 14,
               min_level=2, phases=("plan", "write", "edit")),
        Recipe("herbs", "pet_game_recipe_herbs", "Grow herbs", "gardening", 150000, 5, 0, 5,
               outputs={"herb": 2}, phases=("sow", "water", "harvest")),
        Recipe("flowers", "pet_game_recipe_flowers", "Grow flowers", "gardening", 240000, 5, 0, 8,
               outputs={"flower": 2}, min_level=2, phases=("sow", "water", "harvest")),
        Recipe("toy", "pet_game_recipe_toy", "Make a toy", "crafting", 180000, 7, 0, 6,
               inputs={"wood": 2}, outputs={"toy": 1}, phases=("choose", "shape", "finish")),
        Recipe("stool", "pet_game_recipe_stool", "Build a stool", "crafting", 300000, 8, 0, 12,
               inputs={"wood": 4}, outputs={"furniture:stool": 1}, min_level=2,
               phases=("choose", "shape", "finish")),
    ]


def _items() -> list[ItemDefinition]:
    return [
        ItemDefinition("wood", "pet_game_item_wood", "Wood", "material", buy_price=3, sell_price=1),
        ItemDefinition("herb", "pet_game_item_herb", "Herbs", "food", sell_price=2),
        ItemDefinition("flower", "pet_game_item_flower", "Flowers", "goods", sell_price=6),
        ItemDefinition("toy", "pet_game_item_toy", "Toy", "goods", sell_price=24),
    ]


def builtin_catalog() -> Catalog:
    """The playable built-in content; content packs extend this through the same checks."""
    return Catalog(_furniture(), _recipes(), _items())


STARTER_KIT = {"furniture:bed_basic": 1, "furniture:table_basic": 1, "furniture:desk_basic": 1}
STARTER_COINS = 10
