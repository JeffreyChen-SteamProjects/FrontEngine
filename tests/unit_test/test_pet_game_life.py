"""Residents live on their own: placement, the first loop, cancellation and replay."""
import pytest

from frontengine.utils.pet_game import simulation, snapshot
from frontengine.utils.pet_game.catalog import CELL_PIXELS, builtin_catalog
from frontengine.utils.pet_game.world import World

HOME = "a" * 32
PET = "b" * 32
MINUTE = 60000


def _profile(identifier: str = PET, **values) -> dict:
    return {"id": identifier, "name": "Mochi", "mood": 60, "fullness": 70, "affection": 3,
            "energy": 70, **values}


def _home(seed: int = 7, width: int = 40) -> tuple[World, str]:
    world = World(builtin_catalog(), HOME, seed=seed)
    world.automatic = False            # these tests check the bare mechanics; automation has its own
    zone = world.add_zone("screen", 0, 900, width)
    world.grant_starter_kit()
    return world, zone


def _furnished(seed: int = 7) -> tuple[World, str]:
    world, zone = _home(seed)
    assert world.place("bed_basic", zone, 2)[0] == "accepted"
    assert world.place("table_basic", zone, 7)[0] == "accepted"
    assert world.place("desk_basic", zone, 12)[0] == "accepted"
    assert world.add_resident(_profile(), zone) == "accepted"
    world.residents[PET].traits = ()         # these tests measure the base rules, not a personality
    return world, zone


def _run(world: World, milliseconds: int) -> list[dict]:
    events = []
    for _ in range(milliseconds // simulation.STEP_MS):
        simulation.step(world)
        events += world.drain_events()
    return events


@pytest.mark.parametrize("cell, problem", [(-1, "outside_zone"), (38, "outside_zone"),
                                           (0, "entrance_blocked"), (13, "overlap")])
def test_placement_explains_why_it_fails(cell, problem):
    world, zone = _home()
    world.place("desk_basic", zone, 12)
    assert world.preview("bed_basic", zone, cell) == problem
    assert world.place("bed_basic", zone, cell) == (problem, None)
    assert world.stored("bed_basic") == 1


def test_restricted_cells_and_decorations():
    world, zone = _home()
    world.zones[zone].restricted = (20,)
    assert world.preview("bed_basic", zone, 18) == "restricted"
    world.place("desk_basic", zone, 12)
    world.ledger.apply("gift", "test", 30)
    world.buy("plant_pot", "p1")
    assert world.place("plant_pot", zone, 13)[0] == "accepted"   # decorations do not block


def test_flipped_furniture_moves_its_interaction_point():
    world, zone = _home()
    _status, identifier = world.place("bed_basic", zone, 4, flipped=True)
    piece = world.furniture[identifier]
    definition = world.definition(piece)
    assert piece.point_cell(definition, 0) == 4 + definition.width - 1 - definition.points[0]


def test_first_loop_work_pays_rest_and_buy_within_fifteen_minutes():
    world, _zone = _furnished()
    assert world.create_task("letter", PET, units=5)[0] == "accepted"
    events = _run(world, 15 * MINUTE)
    kinds = [event["kind"] for event in events]
    settled = [event for event in events if event["kind"] == "settled"]
    assert len(settled) >= 3
    assert any(event["kind"] == "activity" and event["activity"] == "sleep" for event in events)
    assert "completed" in kinds
    assert world.buy("plant_pot", "first-buy") == "accepted"
    assert world.residents[PET].skills["writing"] == 5 * len(settled)


def test_needs_stay_in_range_and_time_only_moves_through_advance():
    world, _zone = _furnished()
    before = world.time_ms
    assert simulation.advance(world, 199) == 0
    assert world.time_ms == before
    assert simulation.advance(world, 1) == 1
    for bad in (-1, 1.5, simulation.MAX_ADVANCE_MS + 1):
        with pytest.raises(ValueError):
            simulation.advance(world, bad)
    _run(world, 60 * MINUTE)
    assert all(0 <= value <= 100 for value in world.residents[PET].needs.values())


def test_same_seed_and_commands_replay_identically():
    def play(seed):
        world, zone = _furnished(seed)
        world.create_task("letter", PET, units=3)
        _run(world, 4 * MINUTE)
        world.command(PET, "eat")
        _run(world, 9 * MINUTE)
        return snapshot.to_dict(world)
    first, second = play(3), play(3)
    assert first == second


def test_cancelled_work_never_pays_and_keeps_nothing_reserved():
    world, _zone = _furnished()
    _status, task = world.create_task("letter", PET)
    _run(world, MINUTE)
    assert world.tasks[task].progress_ms > 0
    assert world.cancel_task(task) == "accepted"
    _run(world, 3 * MINUTE)
    assert world.ledger.coins == 10
    assert not world.ledger.reserved
    assert not any(piece.users for piece in world.furniture.values())


def test_moving_used_furniture_interrupts_and_resumes_with_progress():
    world, zone = _furnished()
    _status, task = world.create_task("letter", PET)
    _run(world, MINUTE)
    progress = world.tasks[task].progress_ms
    desk = next(key for key, piece in world.furniture.items() if piece.definition == "desk_basic")
    assert world.move(desk, 20) == "accepted"
    assert world.residents[PET].activity is None
    assert world.tasks[task].state == "paused"
    assert world.tasks[task].progress_ms == progress
    assert not world.furniture[desk].users
    events = _run(world, 2 * MINUTE)
    assert any(event["kind"] == "settled" for event in events)


def test_storing_a_station_keeps_the_order_and_its_progress():
    world, _zone = _furnished()
    _status, task = world.create_task("letter", PET)
    _run(world, MINUTE)
    desk = next(key for key, piece in world.furniture.items() if piece.definition == "desk_basic")
    progress = world.tasks[task].progress_ms
    assert world.store(desk) == "accepted"
    assert world.stored("desk_basic") == 1
    assert world.tasks[task].state == "paused"
    assert world.tasks[task].progress_ms == progress
    _run(world, MINUTE)
    assert world.tasks[task].progress_ms == progress     # no station, no progress


def test_dragging_and_parking_release_furniture_without_stopping_others():
    world, zone = _furnished()
    other = "c" * 32
    world.add_resident(_profile(other, name="Pip"), zone)
    world.create_task("letter", PET)
    _run(world, 30000)
    assert world.drag(PET, None) == "accepted"
    assert world.residents[PET].activity.kind == "drag"
    assert not any(PET in piece.users.values() for piece in world.furniture.values())
    world.drag(PET, 10**9)
    assert world.residents[PET].x_milli < world.zones[zone].width_pixels * 1000
    assert world.park(PET, True) == "accepted"
    frozen = dict(world.residents[PET].needs), world.residents[PET].x_milli
    other_before = world.residents[other].x_milli, dict(world.residents[other].needs)
    _run(world, 2 * MINUTE)
    assert (dict(world.residents[PET].needs), world.residents[PET].x_milli) == frozen
    assert (world.residents[other].x_milli, dict(world.residents[other].needs)) != other_before


def test_direct_commands_are_refused_with_a_reason():
    world, _zone = _furnished()
    assert world.command(PET, "work") == "no_task"
    world.create_task("letter", PET)
    world.residents[PET].needs["energy"] = 20
    assert world.command(PET, "work") == "too_tired"
    assert world.residents[PET].last_refusal == "too_tired"
    assert world.command(PET, "play") == "no_furniture"
    assert world.command(PET, "sleep") == "accepted"
    _run(world, 2000)
    assert world.residents[PET].activity.kind == "sleep"


def test_low_energy_slows_work_and_exhaustion_sends_the_pet_to_bed():
    world, _zone = _furnished()
    _status, task = world.create_task("letter", PET)
    _run(world, 20000)
    world.residents[PET].needs["energy"] = 28
    before = world.tasks[task].progress_ms
    _run(world, 10000)
    assert world.tasks[task].progress_ms - before <= 5200
    world.residents[PET].needs["energy"] = 15
    _run(world, 400)
    assert world.residents[PET].activity.kind == "sleep"
    assert world.tasks[task].state == "paused"


def test_without_furniture_basic_rest_and_food_are_still_available():
    world, zone = _home()
    world.add_resident(_profile(energy=5, fullness=90), zone)
    _run(world, 1000)
    assert world.residents[PET].activity.kind == "nap"
    world.residents[PET].activity = None
    world.residents[PET].needs.update(energy=90, fullness=10)
    _run(world, 1000)
    assert world.residents[PET].activity.kind == "snack"


def test_owned_beds_are_not_taken_by_other_residents():
    world, zone = _furnished()
    other = "c" * 32
    world.add_resident(_profile(other, name="Pip", energy=5), zone)
    bed = next(key for key, piece in world.furniture.items() if piece.definition == "bed_basic")
    assert world.assign_bed(bed, PET) == "accepted"
    _run(world, 1000)
    assert world.residents[other].activity.kind == "nap"


def test_six_residents_share_little_furniture_for_three_game_days():
    world, zone = _home(seed=11, width=48)
    world.ledger.apply("gift", "test", 500, {"furniture:desk_basic": 1})
    for definition, cell in (("bed_basic", 2), ("table_basic", 7), ("desk_basic", 12), ("desk_basic", 16)):
        world.place(definition, zone, cell)
    for definition, cell in (("toy_box", 20), ("armchair", 23)):
        world.buy(definition, "buy-" + definition)
        world.place(definition, zone, cell)
    residents = [f"{index:032x}" for index in range(1, 7)]
    for identifier in residents:
        world.add_resident(_profile(identifier), zone)
        world.create_task("letter", identifier, units=20)
    seen = {identifier: set() for identifier in residents}
    for event in _run(world, 180 * MINUTE):
        if event["kind"] in ("completed", "settled"):
            seen[event["resident"]].add(event.get("activity", event["kind"]))
    for identifier in residents:
        assert "settled" in seen[identifier]          # diligent pets go straight on to the next unit
        assert seen[identifier] & {"sleep", "nap"}
        assert seen[identifier] & {"eat", "snack"}
    holders = [user for piece in world.furniture.values() for user in piece.users.values()]
    assert len(holders) == len(set(holders))
    for piece in world.furniture.values():
        for user in piece.users.values():
            assert world.residents[user].activity.furniture == piece.identifier


def test_same_identity_cannot_live_twice_and_leaving_cleans_references():
    world, zone = _furnished()
    assert world.add_resident(_profile(), zone) == "duplicate"
    bed = next(key for key, piece in world.furniture.items() if piece.definition == "bed_basic")
    world.assign_bed(bed, PET)
    world.create_task("letter", PET)
    _run(world, 30000)
    assert world.remove_resident(PET) == "accepted"
    assert world.furniture[bed].owner is None
    assert not world.tasks
    assert not any(piece.users for piece in world.furniture.values())


def test_resident_starts_at_the_entrance_in_zone_coordinates():
    world, zone = _home()
    world.add_resident(_profile(), zone)
    assert world.residents[PET].x_milli == CELL_PIXELS // 2 * 1000


def test_queued_work_refusal_remains_visible_until_next_accepted_activity():
    from frontengine.show.pet_game.captions import activity_text, result_text

    world, _zone = _furnished()
    resident = world.residents[PET]
    resident.needs["energy"] = 26
    resident.accumulators["energy"] = -59800
    assert world.create_task("letter", PET)[0] == "accepted"
    world.drain_events()
    assert world.command(PET, "work") == "accepted"

    simulation.step(world)
    assert resident.needs["energy"] == 25
    assert any(event["kind"] == "refused" and event["reason"] == "too_tired"
               for event in world.drain_events())
    assert result_text("too_tired") in activity_text(resident, world)

    assert world.command(PET, "sleep") == "accepted"
    simulation.step(world)
    assert resident.activity.kind == "sleep"
    assert result_text("too_tired") not in activity_text(resident, world)
