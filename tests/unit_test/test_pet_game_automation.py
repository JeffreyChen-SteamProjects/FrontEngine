"""The home runs itself: furniture sets itself out, pets take up work, rewards are collected."""
import pytest

from frontengine.utils.pet_game import behaviour, goals, simulation
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.schedule import HOUR_MS
from frontengine.utils.pet_game.world import World

HOME = "a" * 32
PET = "b" * 32


def _home(width: int = 40, coins: int = 0) -> tuple[World, str]:
    world = World(builtin_catalog(), HOME, seed=5)
    zone = world.add_zone("screen", 0, 900, width)
    world.grant_starter_kit()
    if coins:
        world.ledger.apply("gift", "test", coins)
    return world, zone


def _pet(world: World, zone: str, identifier: str = PET) -> str:
    world.add_resident({"id": identifier, "name": "Mochi", "mood": 70, "fullness": 80, "affection": 3,
                        "energy": 90}, zone)
    return identifier


def _run(world: World, milliseconds: int) -> list[dict]:
    events = []
    for _ in range(milliseconds // simulation.STEP_MS):
        simulation.step(world)
        events += world.drain_events()
    return events


def test_the_starter_kit_sets_itself_out_with_room_between_pieces():
    world, zone = _home()
    assert world.furnish(zone) == 3
    cells = sorted((piece.cell, world.definition(piece).width) for piece in world.furniture.values())
    for (cell, width), (following, _width) in zip(cells, cells[1:]):
        assert following - (cell + width) >= 1
    assert all(not world.stored(name) for name in ("bed_basic", "table_basic", "desk_basic"))
    assert world.furnish(zone) == 0                     # nothing left to set out


def test_bought_furniture_goes_straight_into_the_home_or_waits_when_there_is_no_room():
    world, zone = _home(width=40, coins=500)
    world.furnish(zone)
    assert world.buy_and_place("armchair", zone, "t1") == "accepted"
    assert not world.stored("armchair")
    assert any(piece.definition == "armchair" for piece in world.furniture.values())
    cramped, small = _home(width=14, coins=500)
    cramped.furnish(small)
    assert cramped.buy_and_place("workbench", small, "t2") == "bought_no_room"
    assert cramped.stored("workbench") == 1
    assert world.free_cell("nonexistent", zone) is None


def test_an_idle_pet_takes_up_the_job_of_its_trade_during_work_hours():
    world, zone = _home()
    world.furnish(zone)
    _pet(world, zone)
    world.time_ms = 10 * HOUR_MS                         # inside the standard routine's work block
    events = _run(world, 60000)
    taken = [event for event in events if event["kind"] == "auto_job"]
    assert taken
    assert taken[0]["resident"] == PET
    task = next(iter(world.tasks.values()))
    assert world.catalog.recipes[task.recipe].profession == "writing"   # the only workstation is the desk


def test_jobs_needing_missing_materials_are_never_chosen():
    world, zone = _home(coins=500)
    world.furnish(zone)
    world.buy_and_place("workbench", zone, "t1")
    _pet(world, zone)
    resident = world.residents[PET]
    resident.traits = ("handy", "cheerful")                       # crafting is its trade
    identifier = behaviour.auto_task(world, resident)
    recipe = world.catalog.recipes[world.tasks[identifier].recipe]
    assert all(world.ledger.available(item) >= count for item, count in recipe.inputs.items())


def test_no_job_without_a_workstation_and_none_while_automation_is_off():
    world, zone = _home()
    _pet(world, zone)
    assert behaviour.auto_task(world, world.residents[PET]) is None
    world.furnish(zone)
    world.automatic = False
    world.time_ms = 10 * HOUR_MS
    _run(world, 60000)
    assert not world.tasks


def test_finished_tutorial_goals_and_affordable_commissions_settle_themselves():
    world, zone = _home()
    world.furnish(zone)
    _pet(world, zone)
    goals.refresh_commissions(world)
    offer = world.progress.commissions["offers"][0]
    world.ledger.apply("gift-items", "test", items={offer["item"]: offer["count"]})
    coins = world.ledger.coins
    world.progress.next_check_ms = 0
    goals.update(world)
    events = world.drain_events()
    kinds = {event["kind"] for event in events}
    assert "goal_claimed" in kinds
    assert "commission_done" in kinds
    assert world.progress.goals["move_in"] == "claimed"
    assert world.ledger.coins > coins


def test_skipped_tutorials_stay_unclaimed():
    world, zone = _home()
    world.furnish(zone)
    _pet(world, zone)
    goals.skip_tutorial(world)
    world.progress.next_check_ms = 0
    goals.update(world)
    assert not [event for event in world.drain_events() if event["kind"] == "goal_claimed"]


@pytest.mark.parametrize("reason", ["waiting_materials", "no_station", "station_busy"])
def test_blocked_work_reason_is_visible_until_work_resumes(reason):
    from frontengine.show.pet_game.captions import activity_text, result_text

    world, zone = _home(coins=500)
    world.automatic = False
    _pet(world, zone)
    resident = world.residents[PET]
    recipe = "toy" if reason == "waiting_materials" else "letter"
    if reason == "waiting_materials":
        assert world.buy_and_place("workbench", zone, "bench") == "accepted"
    elif reason == "station_busy":
        world.furnish(zone)
        other = _pet(world, zone, "c" * 32)
        assert world.create_task("letter", other)[0] == "accepted"
        behaviour.decide(world, world.residents[other])
        assert world.residents[other].activity.kind == "work"
    assert world.create_task(recipe, PET)[0] == "accepted"

    behaviour.decide(world, resident)
    assert resident.activity.kind != "work"
    assert result_text(reason) in activity_text(resident, world)

    if reason == "waiting_materials":
        world.ledger.apply("wood", "test", items={"wood": 2})
    elif reason == "no_station":
        world.furnish(zone)
    else:
        behaviour.cancel_activity(world, world.residents[other], "test")
    behaviour.cancel_activity(world, resident, "test")
    behaviour.decide(world, resident)
    assert resident.activity.kind == "work"
    assert result_text(reason) not in activity_text(resident, world)


@pytest.mark.parametrize("reason", ["waiting_materials", "no_station", "station_busy"])
def test_manual_work_reports_start_failure_and_can_retry(reason):
    from frontengine.show.pet_game.captions import activity_text, result_text

    world, zone = _home(coins=500)
    world.automatic = False
    world.time_ms = 0
    _pet(world, zone)
    resident = world.residents[PET]
    recipe = "toy" if reason == "waiting_materials" else "letter"
    if reason == "waiting_materials":
        assert world.buy_and_place("workbench", zone, "bench") == "accepted"
    elif reason == "station_busy":
        world.furnish(zone)
        other = _pet(world, zone, "c" * 32)
        assert world.create_task("letter", other)[0] == "accepted"
        assert behaviour.start_work(world, world.residents[other], "command") is None
    assert world.create_task(recipe, PET)[0] == "accepted"
    world.drain_events()
    assert world.command(PET, "work") == "accepted"

    simulation.step(world)
    refused = [event for event in world.drain_events() if event["kind"] == "refused"]
    assert [event["reason"] for event in refused] == [reason]
    assert refused[0]["command"] == "work" and refused[0]["resident"] == PET
    assert result_text(reason) in activity_text(resident, world)

    if reason == "waiting_materials":
        world.ledger.apply("wood", "test", items={"wood": 2})
    elif reason == "no_station":
        world.furnish(zone)
    else:
        behaviour.cancel_activity(world, world.residents[other], "test")
    assert world.command(PET, "work") == "accepted"
    simulation.step(world)
    assert resident.activity.kind == "work"
    assert result_text(reason) not in activity_text(resident, world)
    assert not [event for event in world.drain_events() if event["kind"] == "refused"]
