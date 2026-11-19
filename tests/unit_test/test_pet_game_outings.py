"""Desktop outings in the home simulation: a free-time activity offered only while the page allows
it, short, never saved, and ended by commands, a drag, urgent needs or the page calling pets home."""
import pytest

from frontengine.utils.pet_game import simulation, snapshot
from frontengine.utils.pet_game.behaviour import OUTING_MS, _free_choices, _start_free
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.world import World

HOME = "b" * 32
PET = f"{1:032x}"


def _world() -> World:
    world = World(builtin_catalog(), HOME, seed=3)
    zone = world.add_zone("screen", 0, 900, 40)
    world.grant_starter_kit()
    world.add_resident({"id": PET, "name": "Mochi", "mood": 80, "fullness": 90, "affection": 0,
                        "energy": 90}, zone)
    return world


def _go_out(world: World, monkeypatch) -> None:
    """Make the next free-time choice an outing and take it."""
    resident = world.residents[PET]
    resident.activity = None
    monkeypatch.setattr(world.rng, "weighted", lambda pairs: "outing")
    _start_free(world, resident)
    monkeypatch.undo()


def _kinds(world: World, reason: str = "free_time") -> set[str]:
    return {kind for kind, _weight in _free_choices(world, world.residents[PET], reason)}


def test_an_outing_is_offered_only_while_the_page_allows_it():
    world = _world()
    assert "outing" not in _kinds(world)                  # off until a desktop strip can show it
    world.set_outings(True)
    assert "outing" in _kinds(world)
    assert "outing" not in _kinds(world, "cheer_up")      # a glum pet looks for something at home


def test_an_outing_is_short_lifts_the_mood_and_ends_by_itself(monkeypatch):
    world = _world()
    world.set_outings(True)
    _go_out(world, monkeypatch)
    activity = world.residents[PET].activity
    assert activity.kind == "outing"
    assert OUTING_MS[0] <= activity.until_ms - world.time_ms <= OUTING_MS[1]
    simulation.advance(world, simulation.STEP_MS * 2)
    assert activity.phase == "using"                      # it leaves from where it stood
    world.residents[PET].needs["mood"] = 50
    world.drain_events()
    simulation.advance(world, OUTING_MS[1] + 2000)
    events = world.drain_events()
    assert {"kind": "completed", "resident": PET, "activity": "outing"} in [
        {key: event[key] for key in ("kind", "resident", "activity") if key in event} for event in events]
    assert world.residents[PET].needs["mood"] > 50


def test_forbidding_outings_calls_every_pet_home(monkeypatch):
    world = _world()
    world.set_outings(True)
    _go_out(world, monkeypatch)
    assert world.set_outings(False) == [PET]
    assert world.residents[PET].activity is None
    assert world.set_outings(False) == []                 # nobody is out any more


def test_come_home_ends_only_an_outing(monkeypatch):
    world = _world()
    world.set_outings(True)
    assert world.call_home(PET) == "not_out"
    assert world.call_home("f" * 32) == "unknown"
    _go_out(world, monkeypatch)
    assert world.call_home(PET) == "accepted"
    assert world.residents[PET].activity is None


@pytest.mark.parametrize("change", ["command", "drag", "hungry"])
def test_commands_a_drag_and_urgent_needs_end_an_outing(monkeypatch, change):
    world = _world()
    world.set_outings(True)
    _go_out(world, monkeypatch)
    resident = world.residents[PET]
    if change == "command":
        assert world.command(PET, "stop") == "accepted"
        assert resident.activity is None
    elif change == "drag":
        world.drag(PET, None)
        assert resident.activity.kind == "drag"
    else:
        simulation.advance(world, simulation.STEP_MS * 2)
        resident.needs["fullness"] = 5
        simulation.advance(world, simulation.STEP_MS)
        assert resident.activity is None or resident.activity.kind != "outing"


def test_go_out_sends_a_pet_out_at_once_like_any_instruction():
    world = _world()
    world.set_outings(True)
    resident = world.residents[PET]
    resident.commands.append("sleep")
    assert world.go_out(PET) == "accepted"
    assert resident.activity.kind == "outing" and resident.activity.reason == "command"
    assert resident.commands == []                         # a queued instruction gives way
    assert OUTING_MS[0] <= resident.activity.until_ms - world.time_ms <= OUTING_MS[1]
    simulation.advance(world, simulation.STEP_MS)
    assert resident.activity.phase == "using"


@pytest.mark.parametrize("case, code", [("off", "outings_off"), ("out", "already_out"),
                                        ("hungry", "needs_care"), ("tired", "needs_care"),
                                        ("unknown", "unknown"), ("parked", "parked")])
def test_go_out_says_why_a_pet_stays_in(case, code):
    world = _world()
    world.set_outings(case != "off")
    resident = world.residents[PET]
    if case == "out":
        world.go_out(PET)
    elif case == "hungry":
        resident.needs["fullness"] = 5
    elif case == "tired":
        resident.needs["energy"] = 5
    elif case == "parked":
        resident.parked = True
    assert world.go_out("f" * 32 if case == "unknown" else PET) == code
    if case not in ("out", "unknown", "parked"):
        assert resident.activity is None or resident.activity.kind != "outing"


def test_outings_are_never_saved(monkeypatch):
    world = _world()
    world.set_outings(True)
    _go_out(world, monkeypatch)
    loaded = snapshot.from_dict(snapshot.to_dict(world), builtin_catalog())
    assert loaded.outings_allowed is False
    assert loaded.residents[PET].activity is None         # activities are runtime only
