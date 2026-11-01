"""Compare main-window startup, command search and page switching between two checkouts.

Run from the repository root::

    git worktree add ../fe-baseline <baseline-commit>
    py -m benchmarks.startup_compare --baseline ../fe-baseline --rounds 8 --output docs/benchmarks/<file>.json

Each round starts a fresh spawned process for the baseline and then for this
checkout (interleaved, so machine noise affects both), in a temporary working
directory with English settings and the offscreen platform. The child puts the
chosen checkout first on ``sys.path`` and times ``FrontEngineMainUI()``
construction, a command search for "pet" and visiting every page. One warm-up
round per side is not counted (a new worktree compiles bytecode on first use).
The plan's rule (progress.md #31): p95 may not grow by more than 10% or 50 ms,
whichever is larger.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _probe(checkout: str, results) -> None:
    """Runs in a spawned child: nothing from either checkout is imported before this."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    sys.path.insert(0, checkout)
    with tempfile.TemporaryDirectory() as folder:
        os.chdir(folder)
        Path("user_setting.json").write_text('{"language": "English"}', encoding="utf-8")
        from PySide6.QtWidgets import QApplication
        app = QApplication([])
        started = time.perf_counter()
        from frontengine.ui.main_ui import FrontEngineMainUI
        window = FrontEngineMainUI(main_app=None, show_system_tray_ray=False, redirect_output=False)
        startup = time.perf_counter() - started
        started = time.perf_counter()
        window.open_command_palette()
        window.command_palette.search_input.setText("pet")
        window.command_palette.refresh()
        search = time.perf_counter() - started
        window.command_palette.close()
        switches = []
        for index in range(window.page_stack.count()):
            started = time.perf_counter()
            window.sidebar.select_page(index)
            app.processEvents()
            switches.append(time.perf_counter() - started)
        window.close()
        os.chdir(ROOT)
    results.put({"startup_ms": startup * 1000, "search_ms": search * 1000,
                 "page_switch_ms": max(switches) * 1000, "pages": len(switches)})


def run_once(checkout: Path) -> dict:
    context = multiprocessing.get_context("spawn")
    results = context.Queue()
    child = context.Process(target=_probe, args=(str(checkout.resolve()), results))
    child.start()
    sample = results.get(timeout=300)
    child.join(60)
    return sample


def p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))]


def inside_repository(path: Path) -> Path:
    """Results go somewhere under this checkout (normally docs/benchmarks/), never elsewhere."""
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT):
        raise SystemExit(f"--output must be inside {ROOT}")
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--rounds", type=int, default=6)
    parser.add_argument("--warmup", type=int, default=1, help="uncounted rounds (bytecode caches, disk)")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not (args.baseline / "frontengine" / "__init__.py").is_file():
        raise SystemExit("--baseline must be a FrontEngine checkout")
    samples = {"baseline": [], "current": []}
    for _ in range(args.warmup):
        run_once(args.baseline)
        run_once(ROOT)
    for _ in range(args.rounds):
        samples["baseline"].append(run_once(args.baseline))
        samples["current"].append(run_once(ROOT))
    report = {"rounds": args.rounds, "warmup": args.warmup, "metrics": {}}
    for metric in ("startup_ms", "search_ms", "page_switch_ms"):
        base = p95([sample[metric] for sample in samples["baseline"]])
        now = p95([sample[metric] for sample in samples["current"]])
        allowed = max(base * 0.10, 50.0)
        report["metrics"][metric] = {"baseline_p95": round(base, 2), "current_p95": round(now, 2),
                                     "allowed_increase": round(allowed, 2), "within": now - base <= allowed}
    report["pages"] = {"baseline": samples["baseline"][0]["pages"], "current": samples["current"][0]["pages"]}
    text = json.dumps(report, indent=2)
    if args.output:
        inside_repository(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if all(metric["within"] for metric in report["metrics"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
