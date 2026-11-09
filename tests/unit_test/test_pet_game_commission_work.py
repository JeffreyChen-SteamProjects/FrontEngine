"""Sending a pet to make what a commission asks for: who goes, how much, and why not."""
import pytest

from frontengine.utils.pet_game import commission_work, simulation
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.commission_work import PRIORITY, dispatch, plan
from frontengine.utils.pet_game.resident import LEVEL_STEPS
from frontengine.utils.pet_game.world import World

HOME, MOCHI, PIP = "a" * 32, "b" * 32, "c" * 32
MINUTE = 60000


def _home(*residents: str) -> tuple[World, str]:
    world = World(builtin_catalog(), HOME, seed=4)
    world.automatic = False
    zone = world.add_zone("screen", 0, 900, 48)
    world.grant_starter_kit()
    world.ledger.apply("gift", "test", 5000)
    for definition, cell in (("bed_basic", 2), ("table_basic", 7), ("desk_basic", 12)):
        world.place(definition, zone, cell)
    for identifier in residents or (MOCHI,):
        world.add_resident({"id": identifier, "name": identifier[:4], "mood": 80, "fullness": 90,
                            "affection": 0, "energy": 95}, zone)
        world.residents[identifier].traits = ()
    return world, zone


def _station(world: World, zone: str, definition: str, cell: int = 20) -> str:
    assert world.buy(definition, "buy-" + definition + str(cell)) == "accepted"
    status, identifier = world.place(definition, zone, cell)
    assert status == "accepted"
    return identifier


def _offer(world: World, item: str, count: int, coins: int = 30) -> int:
    world.progress.commissions = {"day": 0, "offers": [{"item": item, "count": count, "coins": coins,
                                                         "done": False}]}
    return 0


def _level(world: World, resident: str, profession: str, level: int) -> None:
    world.residents[resident].skills[profession] = LEVEL_STEPS[level - 1]


def test_the_pet_with_a_planter_is_sent_for_the_missing_herbs_and_the_commission_is_handed_in():
    world, zone = _home()
    _station(world, zone, "planter")
    index = _offer(world, "herb", 5)
    sent = dispatch(world, index)
    assert (sent.result, sent.resident, sent.recipe, sent.units) == ("accepted", MOCHI, "herbs", 3)  # 2 per unit
    [task] = world.tasks.values()
    assert task.priority == PRIORITY and task.units == 3 and task.resident == MOCHI
    assert "work" in world.residents[MOCHI].commands
    world.automatic = True                     # handing in is the home's automation
    for _ in range(40 * MINUTE // simulation.STEP_MS):
        simulation.step(world)
        if world.progress.commissions["offers"][index]["done"]:
            break
    assert world.progress.commissions["offers"][index]["done"]
    assert any(event["kind"] == "commission_done" for event in world.drain_events())


def test_stored_items_and_open_orders_are_counted_first():
    world, zone = _home()
    _station(world, zone, "planter")
    assert world.ledger.apply("herbs-in-store", "test", 0, {"herb": 2}) == "accepted"
    index = _offer(world, "herb", 5)
    assert plan(world, index).units == 2                     # 3 still missing: two units of two
    assert dispatch(world, index).result == "accepted"
    assert dispatch(world, index).result == "already_queued"
    assert len(world.tasks) == 1


def test_a_commission_that_can_already_be_filled_is_handed_in_at_once():
    world, _zone = _home()
    assert world.ledger.apply("toys", "test", 0, {"toy": 1}) == "accepted"
    index = _offer(world, "toy", 1, coins=40)
    coins = world.ledger.coins
    assert dispatch(world, index).result == "delivered"
    assert world.progress.commissions["offers"][index]["done"]
    assert world.ledger.coins > coins and not world.tasks


@pytest.mark.parametrize("setup, item, result", [
    ("none", "herb", "no_station"),
    ("planter", "flower", "skill_too_low"),
    ("workbench", "toy", "missing_materials"),
])
def test_why_no_pet_can_go_is_said_and_nothing_is_created(setup, item, result, monkeypatch):
    world, zone = _home()
    monkeypatch.setattr(commission_work, "unlocked", lambda _world, _level: True)   # flowers open at level 2
    if setup != "none":
        _station(world, zone, setup)
    index = _offer(world, item, 3 if item == "herb" else 2)
    sent = dispatch(world, index)
    assert sent.result == result
    assert not world.tasks and not world.residents[MOCHI].commands
    if result == "missing_materials":
        assert sent.missing == {"wood": 4}                    # two toys, two wood each, none stored


def test_a_recipe_the_home_has_not_unlocked_is_refused():
    world, zone = _home()
    _station(world, zone, "planter")
    _level(world, MOCHI, "gardening", 2)
    assert dispatch(world, _offer(world, "flower", 2)).result == "locked"


def test_the_trade_pet_with_the_most_skill_and_least_work_goes_and_hidden_pets_stay():
    world, zone = _home(MOCHI, PIP)
    _station(world, zone, "planter")
    _level(world, MOCHI, "gardening", 2)
    _level(world, PIP, "gardening", 3)
    assert plan(world, _offer(world, "herb", 3)).resident == PIP
    world.residents[MOCHI].traits = ("green_thumb",)
    assert plan(world, 0).resident == MOCHI                   # the trade's own trait comes first
    world.residents[MOCHI].parked = True
    assert plan(world, 0).resident == PIP


def test_a_busy_pet_finishes_what_it_is_doing_and_a_tired_one_starts_later():
    world, zone = _home()
    _station(world, zone, "planter")
    simulation.step(world)
    resident = world.residents[MOCHI]
    before = resident.activity
    sent = dispatch(world, _offer(world, "herb", 3))
    assert sent.result == "accepted" and not sent.later
    assert resident.activity is before                       # nothing it was doing is cut short
    world.cancel_task(next(iter(world.tasks)))
    resident.commands.clear()
    resident.needs["energy"] = 10
    sent = dispatch(world, 0)
    assert sent.result == "accepted" and sent.later
    assert len(world.tasks) == 1 and "work" not in resident.commands


def test_a_finished_or_unknown_commission_is_left_alone():
    world, _zone = _home()
    index = _offer(world, "herb", 3)
    world.progress.commissions["offers"][index]["done"] = True
    assert dispatch(world, index).result == "unknown"
    assert dispatch(world, 7).result == "unknown"
