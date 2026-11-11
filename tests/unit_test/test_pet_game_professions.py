"""Three professions, materials and goods: everything pays once, nothing duplicates, no loops."""
from dataclasses import replace

import pytest

from frontengine.utils.pet_game import simulation
from frontengine.utils.pet_game.catalog import Catalog, ItemDefinition, Recipe, builtin_catalog
from frontengine.utils.pet_game.world import World

HOME, PET = "a" * 32, "b" * 32
MINUTE = 60000


def _home(coins: int = 1000) -> tuple[World, str]:
    world = World(builtin_catalog(), HOME, seed=4)
    world.automatic = False            # these tests check the bare mechanics; automation has its own
    zone = world.add_zone("screen", 0, 900, 48)
    world.grant_starter_kit()
    world.ledger.apply("gift", "test", coins)
    for definition, cell in (("bed_basic", 2), ("table_basic", 7), ("desk_basic", 12)):
        world.place(definition, zone, cell)
    world.add_resident({"id": PET, "name": "Mochi", "mood": 80, "fullness": 90, "affection": 0, "energy": 95}, zone)
    return world, zone


def _station(world: World, zone: str, definition: str, cell: int) -> str:
    assert world.buy(definition, "buy-" + definition) == "accepted"
    status, identifier = world.place(definition, zone, cell)
    assert status == "accepted"
    return identifier


def _run(world: World, minutes: float) -> list[dict]:
    events = []
    for _ in range(int(minutes * MINUTE) // simulation.STEP_MS):
        simulation.step(world)
        events += world.drain_events()
    return events


def test_gardening_grows_herbs_into_storage():
    world, zone = _home()
    _station(world, zone, "planter", 18)
    assert world.create_task("herbs", PET)[0] == "accepted"
    _run(world, 4)
    assert world.ledger.count("herb") == 2
    assert world.residents[PET].skills["gardening"] == 5


def test_crafting_uses_bought_wood_and_sells_the_toy():
    world, zone = _home()
    _station(world, zone, "workbench", 18)
    assert world.buy_item("wood", 2, "wood-1") == "accepted"
    coins = world.ledger.coins
    assert world.create_task("toy", PET)[0] == "accepted"
    _run(world, 4.5)
    assert world.ledger.count("toy") == 1
    assert world.ledger.count("wood") == 0
    assert world.sell_item("toy", 1, "sell-toy") == "accepted"
    assert world.ledger.coins == coins + 24


def test_building_furniture_needs_experience_and_lands_in_storage(monkeypatch):
    from frontengine.utils.pet_game import goals
    world, zone = _home()
    _station(world, zone, "workbench", 18)
    world.buy_item("wood", 4, "wood-1")
    assert world.create_task("stool", PET) == ("skill_too_low", None)
    world.residents[PET].skills["crafting"] = 40
    assert world.create_task("stool", PET) == ("locked", None)          # stools open at home level 3
    monkeypatch.setattr(goals, "home_level", lambda _world: 3)
    assert world.create_task("stool", PET)[0] == "accepted"
    _run(world, 7)
    assert world.stored("stool") == 1
    assert world.place("stool", zone, 24)[0] == "accepted"


def test_work_waits_for_materials_and_never_spends_reserved_wood():
    world, zone = _home()
    _station(world, zone, "workbench", 18)
    _status, task = world.create_task("toy", PET)
    _run(world, 0.5)
    assert world.tasks[task].state == "waiting_materials"
    world.buy_item("wood", 2, "wood-1")
    _run(world, 0.5)
    assert world.ledger.reserved == {"wood": 2}
    assert world.sell_item("wood", 1, "sell-wood") == "none_stored"
    assert world.cancel_task(task) == "accepted"
    assert world.ledger.reserved == {}
    assert world.ledger.count("wood") == 2


def test_putting_the_workbench_away_keeps_the_materials():
    world, zone = _home()
    bench = _station(world, zone, "workbench", 18)
    world.buy_item("wood", 2, "wood-1")
    _status, task = world.create_task("toy", PET)
    _run(world, 1)
    assert world.store(bench) == "accepted"
    assert world.ledger.count("wood") == 2
    assert world.ledger.reserved == {"wood": 2}
    assert world.tasks[task].state == "paused"
    assert world.tasks[task].progress_ms > 0


def test_meals_with_herbs_are_happier_and_use_one_herb():
    def meal(herbs: int) -> int:
        world, _zone = _home()
        if herbs:
            world.ledger.apply("herbs", "test", 0, {"herb": herbs})
        resident = world.residents[PET]
        resident.needs.update(fullness=30, mood=40)
        world.command(PET, "eat")
        _run(world, 0.75)
        assert world.ledger.count("herb") == max(0, herbs - 1)
        return resident.needs["mood"]
    assert meal(3) > meal(0)


def test_shop_rules_for_materials_and_goods():
    world, _zone = _home(coins=0)
    assert world.buy_item("wood", 4, "w") == "insufficient_coins"
    assert world.buy_item("herb", 1, "h") == "not_for_sale"
    assert world.buy_item("wood", 0, "z") == "invalid"
    assert world.sell_item("toy", 1, "t") == "none_stored"


def test_letters_restart_production_from_zero_coins():
    world, _zone = _home(coins=0)
    world.ledger.apply("spend", "test", -world.ledger.coins)
    assert world.ledger.coins == 0
    world.create_task("letter", PET)
    _run(world, 3)
    assert world.ledger.coins == 12


def test_no_item_can_be_bought_and_sold_back_for_profit():
    catalog = builtin_catalog()
    for item in catalog.items.values():
        assert not item.buy_price or item.buy_price > item.sell_price
    with pytest.raises(ValueError):
        Catalog([], [], [ItemDefinition("gold", "k", "Gold", "material", buy_price=5, sell_price=5)])


def test_recipe_loops_are_rejected():
    catalog = builtin_catalog()
    items = list(catalog.items.values())
    there = Recipe("a", "k", "A", "crafting", 60000, 1, 0, 1, inputs={"wood": 1}, outputs={"toy": 1})
    back = Recipe("b", "k", "B", "crafting", 60000, 1, 0, 1, inputs={"toy": 1}, outputs={"wood": 2})
    with pytest.raises(ValueError):
        Catalog(list(catalog.furniture.values()), [there, back], items)
    with pytest.raises(ValueError):
        Catalog(list(catalog.furniture.values()), [replace(there, outputs={"gem": 1})], items)


def test_phases_split_the_work():
    recipe = builtin_catalog().recipes["herbs"]
    assert [recipe.phase_at(ms) for ms in (0, 60000, 120000, 149999)] == ["sow", "water", "harvest", "harvest"]


def test_first_purchases_land_inside_the_balance_targets():
    world, zone = _home(coins=0)
    world.ledger.apply("reset", "test", -world.ledger.coins + 10)
    world.residents[PET].traits = ()          # balance targets are for a resident without likings
    first_decoration = first_station = None
    for minute in range(1, 61):
        if not world.open_tasks(PET):
            world.create_task("letter", PET, units=20)
        _run(world, 1)
        if first_decoration is None and world.ledger.coins >= world.catalog.furniture["plant_pot"].price:
            first_decoration = minute
        if first_station is None and world.ledger.coins >= world.catalog.furniture["planter"].price:
            first_station = minute
    assert first_decoration is not None
    assert first_decoration <= 15
    assert first_station is not None
    assert 30 <= first_station <= 60
