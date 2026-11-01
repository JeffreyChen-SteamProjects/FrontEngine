"""Home economy: idempotent transactions, no negative stock, sound catalog data."""
from dataclasses import replace

import pytest

from frontengine.utils.pet_game.catalog import Catalog, builtin_catalog
from frontengine.utils.pet_game.ledger import APPLIED_MEMORY, JOURNAL_LENGTH, Ledger
from frontengine.utils.pet_game.world import World

HOME = "a" * 32


def test_transaction_applies_once_even_when_retried():
    ledger = Ledger()
    assert ledger.apply("t1:u0", "work", 12, {"flower": 2}) == "accepted"
    assert ledger.apply("t1:u0", "work", 12, {"flower": 2}) == "duplicate"
    assert ledger.coins == 12 and ledger.count("flower") == 2
    assert len(ledger.journal) == 1


def test_spending_is_all_or_nothing_and_never_negative():
    ledger = Ledger()
    ledger.apply("seed", "gift", 5, {"wood": 1})
    assert ledger.apply("buy", "buy", -6, {"chair": 1}) == "insufficient"
    assert ledger.apply("use", "craft", 0, {"wood": -2, "toy": 1}) == "insufficient"
    assert ledger.coins == 5 and ledger.items == {"wood": 1}
    assert not ledger.applied("buy") and not ledger.applied("use")


def test_reserved_items_stay_visible_but_cannot_be_spent_twice():
    ledger = Ledger()
    ledger.apply("seed", "gift", 0, {"wood": 3})
    assert ledger.reserve({"wood": 2})
    assert ledger.count("wood") == 3 and ledger.available("wood") == 1
    assert not ledger.reserve({"wood": 2})
    assert ledger.apply("spend", "craft", 0, {"wood": -2}) == "insufficient"
    ledger.release({"wood": 2})
    assert ledger.available("wood") == 3


def test_ledger_round_trip_keeps_duplicate_protection():
    ledger = Ledger()
    ledger.apply("t9:u0", "work", 7)
    restored = Ledger.from_dict(ledger.to_dict())
    assert restored.apply("t9:u0", "work", 7) == "duplicate"
    assert restored.coins == 7


def test_memory_and_journal_are_bounded():
    ledger = Ledger()
    for index in range(APPLIED_MEMORY + 10):
        ledger.apply(f"x{index}", "gift", 1)
    assert len(ledger.journal) == JOURNAL_LENGTH
    assert len(ledger.to_dict()["applied"]) == APPLIED_MEMORY
    assert ledger.apply(f"x{APPLIED_MEMORY + 9}", "gift", 1) == "duplicate"


@pytest.mark.parametrize("change", [
    {"coins": -1}, {"coins": 1.5}, {"items": {"wood": -1}}, {"items": {"Bad Name": 1}},
    {"reserved": {"wood": 5}}, {"applied": ["bad id!"]}, {"journal": "x"},
])
def test_malformed_ledger_is_rejected(change):
    data = {**Ledger().to_dict(), "items": {"wood": 1}, **change}
    with pytest.raises(ValueError):
        Ledger.from_dict(data)


def test_floats_cannot_enter_the_wallet():
    with pytest.raises(ValueError):
        Ledger.from_dict({**Ledger().to_dict(), "coins": 3.0})


@pytest.mark.parametrize("change", [
    {"width": 0}, {"points": (5,)}, {"category": "rocket"}, {"sell_back": 99},
    {"effects": {"energy": 1.5}}, {"activity": None}, {"identifier": "Bad"},
])
def test_invalid_furniture_definitions_are_rejected(change):
    base = builtin_catalog().furniture["bed_basic"]
    with pytest.raises(ValueError):
        Catalog([replace(base, **change)], [])


def test_duplicate_catalog_identities_are_rejected():
    base = builtin_catalog().furniture["plant_pot"]
    with pytest.raises(ValueError):
        Catalog([base, base], [])


def test_sell_back_never_exceeds_purchase_price():
    for definition in builtin_catalog().furniture.values():
        assert definition.sell_back <= definition.price // 2


def _world() -> World:
    world = World(builtin_catalog(), HOME)
    world.add_zone("screen", 0, 0, 40)
    world.grant_starter_kit()
    return world


def test_starter_kit_is_granted_once_even_when_migration_reruns():
    world = _world()
    coins, items = world.ledger.coins, dict(world.ledger.items)
    assert world.grant_starter_kit() == "duplicate"
    assert world.ledger.coins == coins and world.ledger.items == items


def test_buying_and_selling_cannot_make_money():
    world = _world()
    world.ledger.apply("gift", "test", 100)
    assert world.buy("toy_box", "b1") == "accepted"
    assert world.sell("toy_box", "s1") == "accepted"
    assert world.ledger.coins == 10 + 100 - 40 + 20
    assert world.sell("toy_box", "s2") == "none_stored"


def test_basic_facilities_are_neither_sold_nor_bought():
    world = _world()
    assert world.sell("bed_basic", "s") == "essential"
    assert world.buy("table_basic", "b") == "not_for_sale"
    assert world.stored("bed_basic") == 1


def test_purchase_needs_coins_and_is_idempotent():
    world = _world()
    world.ledger.apply("gift", "test", 10)
    assert world.buy("armchair", "b1") == "insufficient_coins"
    assert world.buy("plant_pot", "b2") == "accepted"
    assert world.buy("plant_pot", "b2") == "duplicate"
    assert world.stored("plant_pot") == 1 and world.ledger.coins == 20 - 15


def test_sandbox_layout_is_unlimited_and_free():
    world = World(builtin_catalog(), HOME, mode="sandbox")
    zone = world.add_zone("screen", 0, 0, 40)
    assert world.place("bed_cozy", zone, 4)[0] == "accepted"
    assert world.place("bed_cozy", zone, 10)[0] == "accepted"
    assert world.ledger.coins == 0 and world.ledger.items == {}
