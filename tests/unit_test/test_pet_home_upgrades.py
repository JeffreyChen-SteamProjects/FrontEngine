"""Workstation upgrades, pets helping at work, and the stock limit for automatic jobs."""
from frontengine.show.pet_game.home_strip import piece_lines
from frontengine.utils.pet_game import behaviour, simulation, snapshot
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.world import UPGRADE_BASE_COINS, World

CATALOG = builtin_catalog()
WORKER, HELPER = "b" * 32, "c" * 32


def _world(mode="manage"):
    world = World(CATALOG, "a" * 32, mode, seed=3)
    zone = world.add_zone("s", 0, 0, 40)
    world.grant_starter_kit()
    world.furnish(zone)
    for identifier, name, x in ((WORKER, "Mochi", 300), (HELPER, "Pip", 600)):
        world.add_resident({"id": identifier, "name": name, "mood": 80, "fullness": 80, "affection": 1,
                            "energy": 90}, zone)
        world.residents[identifier].x_milli = x * 1000
        world.residents[identifier].traits = ("quiet", "bookish")
    return world, zone


def _working(world):
    world.create_task("letter", WORKER)
    worker = world.residents[WORKER]
    assert behaviour.start_work(world, worker, "command") is None
    for _ in range(400):
        simulation.step(world)
        if worker.activity is not None and worker.activity.phase == "using":
            return worker
    raise AssertionError("never reached the desk")


def test_upgrades_cost_coins_rise_to_three_and_survive_a_save():
    world, _zone = _world()
    assert world.upgrade_cost("bed_basic") is None                   # only workstations
    price = max(CATALOG.furniture["desk_basic"].price, UPGRADE_BASE_COINS)
    assert world.upgrade_cost("desk_basic") == price
    coins = world.ledger.coins
    world.ledger.apply("gift", "test", 1000)
    assert world.upgrade("desk_basic", "u1") == "accepted"
    assert world.upgrade("desk_basic", "u1") == "duplicate"          # a repeated request pays nothing
    assert world.upgrade("desk_basic", "u2") == "accepted"           # a new level, its own price
    assert world.station_level("desk_basic") == 3
    assert world.ledger.coins == coins + 1000 - price - 2 * price
    assert world.upgrade("desk_basic", "u3") == "not_upgradable"
    loaded = snapshot.from_dict(snapshot.to_dict(world), CATALOG)
    assert loaded.station_level("desk_basic") == 3


def test_an_upgrade_without_coins_is_refused_and_free_arranging_is_free():
    world, _zone = _world()
    world.ledger.apply("drain", "test", -world.ledger.coins)
    assert world.upgrade("desk_basic", "u1") == "insufficient_coins"
    assert world.station_level("desk_basic") == 1
    sandbox, _zone = _world("sandbox")
    assert sandbox.upgrade_cost("desk_basic") == 0


def test_older_saves_load_without_upgrades():
    world, _zone = _world()
    data = snapshot.to_dict(world)
    data["version"] = 5
    del data["progress"]["upgrades"]
    assert snapshot.from_dict(data, CATALOG).progress.upgrades == {}


def test_an_upgraded_desk_and_a_helper_both_speed_the_work_up():
    world, _zone = _world()
    worker = _working(world)
    task = world.tasks[worker.activity.task]
    before = task.progress_ms
    simulation.step(world)
    base = task.progress_ms - before
    world.progress.upgrades["desk_basic"] = 2
    before = task.progress_ms
    simulation.step(world)
    assert task.progress_ms - before == base * 5 // 4
    helper = world.residents[HELPER]
    assert behaviour._help_partner(world, helper) is worker
    behaviour.start_help(world, helper, worker)
    helper.activity.phase = "using"
    assert behaviour.helpers(world, worker) == 1
    before = task.progress_ms
    simulation.step(world)
    assert task.progress_ms - before > base * 5 // 4
    skill = helper.skills.get("writing", 0)
    behaviour.help_completed(world, helper, WORKER)
    assert helper.skills["writing"] == skill + 1


def test_automatic_jobs_stop_making_goods_once_storage_is_full():
    world, zone = _world()
    world.ledger.apply("gift", "test", 1000)
    world.buy_and_place("planter", zone, "p1")
    resident = world.residents[HELPER]
    resident.traits = ("green_thumb", "quiet")
    world.ledger.apply("herbs", "test", items={"herb": behaviour.AUTO_STOCK_LIMIT})
    task = behaviour.auto_task(world, resident)
    assert task is None or world.tasks[task].recipe != "herbs"


def test_a_station_menu_shows_its_level():
    world, _zone = _world()
    world.progress.upgrades["desk_basic"] = 2
    desk = next(p for p in world.furniture.values() if p.definition == "desk_basic")
    assert "Level 2 · 125% speed" in piece_lines(world, desk)
