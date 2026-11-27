"""Measure the pet home under the plan's fixed loads (progress.md #31).

Run from the repository root::

    py -m benchmarks.pet_home --save

Loads are 1 resident / 10 furniture, 6 / 60 and 12 / 120. For each the world
warms up for ten game minutes, then this records:

* world step time (one 200 ms step, the simulation's whole cost) p50/p95/max;
* operation feedback: a player command through ``HomeService.run`` (command,
  event publication) p95;
* save encoding (serialise + reload check, on the GUI thread) p95;
* desktop strip frame time, software rendering offscreen, p95;
* memory: game data via tracemalloc, and the step-time and memory change from
  minute 10 to two game hours of accelerated time.

This is a developer tool, not a CI assertion. Accelerated time measures cost
per step, not wall-clock behaviour over two real hours.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import tempfile
import tracemalloc
from collections import deque
from datetime import date
from pathlib import Path
from time import perf_counter_ns
from typing import Callable, NamedTuple

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6 import __version__ as pyside_version  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

LOADS = ((1, 10), (6, 60), (12, 120))
BUDGET = {"tick_p95_ms": 5.0, "feedback_p95_ms": 100.0, "game_memory_mb": 200.0}
WARM_STEPS = 10 * 60 * 5
MEASURE_STEPS = 10 * 60 * 5
LONG_STEPS = 2 * 60 * 60 * 5
LONGER_STEPS = 4 * 60 * 60 * 5

BENCHMARK_DOCS = Path(__file__).resolve().parents[1] / "docs" / "benchmarks"


def _percentiles(samples_ns: list[int]) -> dict:
    ordered = sorted(samples_ns)
    pick = lambda share: ordered[min(len(ordered) - 1, int(len(ordered) * share))] / 1e6  # noqa: E731
    return {"p50_ms": round(pick(0.50), 4), "p95_ms": round(pick(0.95), 4), "max_ms": round(ordered[-1] / 1e6, 4),
            "mean_ms": round(statistics.fmean(ordered) / 1e6, 4), "samples": len(ordered)}


def build(residents: int, furniture: int):
    """A zone filled with working furniture first, then decorations, and residents with jobs."""
    from frontengine.utils.pet_game.catalog import builtin_catalog
    from frontengine.utils.pet_game.world import World
    world = World(builtin_catalog(), "f" * 32, seed=31)
    zone = world.add_zone("bench", 0, 0, 160)
    world.grant_starter_kit()
    world.ledger.apply("bench", "bench", 10 ** 6, {"wood": 5000})
    solid = [("bed_basic", 4), ("table_basic", 4), ("desk_basic", 3), ("planter", 2), ("workbench", 3),
             ("toy_box", 2), ("armchair", 2), ("stool", 1)]
    cell, index = 1, 0
    while len(world.furniture) < furniture and cell < 150:
        definition, width = solid[index % len(solid)]
        world.ledger.apply(f"stock{index}", "bench", 0, {"furniture:" + definition: 1})
        if world.place(definition, zone, cell)[0] == "accepted":
            cell += width
        index += 1
    while len(world.furniture) < furniture:
        world.ledger.apply(f"deco{len(world.furniture)}", "bench", 0, {"furniture:plant_pot": 1})
        world.place("plant_pot", zone, 1 + len(world.furniture) % 150)
    for number in range(residents):
        identifier = f"{number + 1:032x}"
        world.add_resident({"id": identifier, "name": f"P{number}", "mood": 70, "fullness": 80, "affection": 0,
                            "energy": 80}, zone)
        world.create_task(("letter", "herbs", "toy")[number % 3], identifier, units=20)
    return world, zone


class Sizes(NamedTuple):
    """How much each measurement runs; the defaults are the plan's, tests pass tiny ones."""
    warm_steps: int = WARM_STEPS
    measure_steps: int = MEASURE_STEPS
    encodes: int = 30
    commands: int = 100
    frames: int = 120
    long_marks: tuple[int, int, int] = (WARM_STEPS, LONG_STEPS, LONGER_STEPS)


def _timed(action: Callable[[int], object], count: int) -> list[int]:
    """Nanoseconds each of ``count`` calls of ``action(number)`` took."""
    samples = []
    for number in range(count):
        started = perf_counter_ns()
        action(number)
        samples.append(perf_counter_ns() - started)
    return samples


def _steps(world, count: int) -> list[int]:
    from frontengine.utils.pet_game import simulation

    def step(_number: int) -> None:
        simulation.step(world)
        world.drain_events()
    return _timed(step, count)


def _close(service, store, storage) -> None:
    """Close in dependency order: the service saves and lets go of the store, then the session."""
    try:
        if service is not None and not service.shutdown():
            raise RuntimeError("the home service did not shut down")
        if store is not None:
            store.close()
    finally:
        storage.close()


def _measure_home(world, zone, folder: Path, sizes: Sizes) -> dict:
    """Save encoding, command feedback and strip frames against a home stored in ``folder``."""
    from frontengine.show.pet_game.home_service import HomeService
    from frontengine.show.pet_game.home_strip import HomeStrip
    from frontengine.user_setting.pet_game_save import HomeSaveStore
    from frontengine.user_setting.pet_profiles import PetProfiles
    from frontengine.user_setting.storage_session import StorageSession
    storage = StorageSession.open(folder)
    store = service = None
    try:
        store = HomeSaveStore(storage, world.catalog)
        encodes = _timed(lambda _number: store.encode(world), sizes.encodes)
        service = HomeService(None, store, PetProfiles({}, lambda: None))
        service.world = world
        first = next(iter(world.residents))
        feedback = _timed(lambda number: service.run(
            lambda w: w.command(first, ("eat", "play", "stop", "sleep")[number % 4])), sizes.commands)
        strip = HomeStrip(service, zone)
        frames = _timed(lambda _number: strip.grab(), sizes.frames)
        strip.close()
        save_bytes = len(store.encode(world))
    finally:
        _close(service, store, storage)
    return {"operation_feedback": _percentiles(feedback), "save_encode": _percentiles(encodes),
            "strip_frame": _percentiles(frames), "save_bytes": save_bytes}


def measure_load(residents: int, furniture: int, folder: Path, sizes: Sizes = Sizes()) -> dict:
    tracemalloc.start()
    try:
        before = tracemalloc.get_traced_memory()[0]
        world, zone = build(residents, furniture)
        _steps(world, sizes.warm_steps)
        steps = _steps(world, sizes.measure_steps)
        data_mb = (tracemalloc.get_traced_memory()[0] - before) / 2 ** 20
        home = _measure_home(world, zone, folder, sizes)
    finally:
        tracemalloc.stop()
    return {"residents": residents, "furniture": len(world.furniture), "world_step": _percentiles(steps),
            **home, "game_data_mb": round(data_mb, 2)}


def measure_long(residents: int, furniture: int, marks: tuple[int, int, int] = Sizes().long_marks) -> dict:
    """Step cost and traced memory of the world at game minute 10, two hours and four hours.

    Only the world is traced: the timing window is a bounded deque, so the
    benchmark's own samples cannot look like growth.
    """
    from frontengine.utils.pet_game import simulation
    world, _zone = build(residents, furniture)
    window: deque[int] = deque(maxlen=3000)
    tracemalloc.start()
    base = tracemalloc.get_traced_memory()[0]
    recorded = {}
    for number in range(1, marks[-1] + 1):
        started = perf_counter_ns()
        simulation.step(world)
        world.drain_events()
        window.append(perf_counter_ns() - started)
        if number in marks:
            recorded[number] = {"memory_mb": round((tracemalloc.get_traced_memory()[0] - base) / 2 ** 20, 4),
                                "step": _percentiles(list(window))}
    tracemalloc.stop()
    early, late = recorded[marks[0]]["memory_mb"], recorded[marks[1]]["memory_mb"]
    return {"residents": residents, "furniture": furniture, "at_10_min": recorded[marks[0]],
            "at_2_hours": recorded[marks[1]], "at_4_hours": recorded[marks[2]],
            "memory_growth_percent": round((late - early) / max(early, 1e-6) * 100, 2),
            "bounded_histories": {"ledger_ids": len(world.ledger._applied), "journal": len(world.ledger.journal),
                                  "life_events": len(world.progress.events), "stats": len(world.progress.stats)}}


def results_file() -> Path:
    """A fixed, dated name in this checkout's docs/benchmarks; nothing from the command line forms the path."""
    return BENCHMARK_DOCS / f"{date.today():%Y-%m-%d}-pet-home.json"


def collect(app: QApplication, loads: tuple[tuple[int, int], ...] = LOADS, long_load: tuple[int, int] = (6, 60),
            sizes: Sizes = Sizes()) -> dict:
    """The whole report: machine, every load, the long run and the budget verdict on the middle load."""
    screen = app.primaryScreen()
    report = {"machine": {"platform": platform.platform(), "processor": platform.processor(),
                          "cpus": os.cpu_count(), "python": sys.version.split()[0], "pyside": pyside_version,
                          "qt_platform": app.platformName(), "screen": screen.name() if screen else None,
                          "device_pixel_ratio": screen.devicePixelRatio() if screen else None,
                          "renderer": "software (offscreen grab)"},
              "budget": BUDGET, "loads": [], "long": None}
    with tempfile.TemporaryDirectory() as folder:
        for residents, furniture in loads:
            report["loads"].append(measure_load(residents, furniture, Path(folder), sizes))
    report["long"] = measure_long(*long_load, sizes.long_marks)
    middle = report["loads"][len(loads) // 2]
    report["within_budget"] = {
        "tick_p95_ms": middle["world_step"]["p95_ms"] <= BUDGET["tick_p95_ms"],
        "feedback_p95_ms": middle["operation_feedback"]["p95_ms"] <= BUDGET["feedback_p95_ms"],
        "game_memory_mb": middle["game_data_mb"] <= BUDGET["game_memory_mb"],
    }
    # The plan treats more than 10% growth between minute 10 and hour 2 as something to investigate.
    report["investigate_memory_growth"] = report["long"]["memory_growth_percent"] > 10
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--save", action="store_true", help="write docs/benchmarks/<today>-pet-home.json")
    args = parser.parse_args()
    report = collect(QApplication.instance() or QApplication(sys.argv))
    text = json.dumps(report, indent=2)
    if args.save:
        results_file().write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if all(report["within_budget"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
