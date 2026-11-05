"""Background smoke run of the pet home: a test save, its own windows, a fixed seed, recorded results.

Usage (from the repository root)::

    py tests/integration/pet_game_smoke.py OUTPUT_DIR [--seed N] [--minutes M] [--residents K]
                                           [--shots S] [--native]

Builds a home in a temporary working directory with test pets (their own ``PetProfiles``,
never the user's settings; the home and pet identities are derived from the seed), lets it live ``M`` effective game minutes through
``simulation.advance`` - deterministic for a seed, independent of the wall clock - and writes
OUTPUT_DIR/result.json: the seed, the minutes, every settlement (resident, task, recipe, coins and
its settlement id, which must never repeat), event counts, each resident's needs and coins at the end, and a fingerprint of the
final save that two runs with the same seed must share. ``S`` screenshots of the overview are
taken at even intervals (only its own widget is grabbed, never the screen).

It refuses to touch anything outside itself: media keys raise instead of being sent, nothing
reads or moves other windows, and it runs offscreen unless ``--native`` is given, in which
case Windows runs it on a separate, freshly created desktop.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))  # test this checkout, never an installed frontengine
sys.path.insert(0, str(Path(__file__).resolve().parent))

MINUTE_MS = 60_000
PET_NAMES = ("Mochi", "Pudding", "Tofu", "Bean", "Sesame", "Clover")


class RefusedOutsideEffect(RuntimeError):
    """The smoke run tried to reach outside its own windows."""


def _refuse_media_keys() -> None:
    """Pressing a real media key would pause whatever the person is listening to."""
    from frontengine.utils.media_keys import media_keys

    def refuse(action, sender=None) -> bool:
        raise RefusedOutsideEffect(f"media key {action!r} refused in the smoke run")
    media_keys.send_media_key = refuse


def _arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("output")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--minutes", type=int, default=60, help="effective game minutes (one game day is 60)")
    parser.add_argument("--residents", type=int, default=3, choices=range(1, len(PET_NAMES) + 1))
    parser.add_argument("--shots", type=int, default=3)
    parser.add_argument("--native", action="store_true", help="run on a separate Windows desktop")
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    options = parser.parse_args(argv)
    if not 1 <= options.minutes <= 24 * 60 or not 0 <= options.shots <= 50:
        parser.error("minutes must be 1-1440 and shots 0-50")
    return options


def _identity(seed: int, label: str) -> str:
    """A fixed 32-hex identity per seed: residents are simulated in identity order and their
    personality, the weather and commissions are derived from identities, so a replay needs them."""
    return hashlib.sha256(f"frontengine-smoke:{seed}:{label}".encode("ascii")).hexdigest()[:32]


def _test_profiles(seed: int, residents: int):
    """Test pets in a settings dict of their own, never the user's."""
    from frontengine.user_setting.pet_profile_schema import profile_defaults
    from frontengine.user_setting.pet_profiles import PetProfiles
    records = {}
    for index, name in enumerate(PET_NAMES[:residents]):
        identifier = _identity(seed, f"pet{index}")
        records[identifier] = {"id": identifier, "name": name, "mood": 60, "fullness": 70, "affection": 0,
                               **profile_defaults()}
    settings = {"pet_profiles": {"version": 2, "migrated": True, "records": records}}
    return PetProfiles(settings, lambda: None), list(records)


def fingerprint(world) -> str:
    """sha256 of the save as written."""
    from frontengine.utils.pet_game import snapshot
    data = snapshot.to_dict(world)
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()


def run(output: Path, seed: int, minutes: int, residents: int, shots: int) -> dict:
    """One smoke run in the current working directory; returns (and writes) the result."""
    from frontengine.show.pet_game.home_service import HomeService
    from frontengine.show.pet_game.home_view import HomeView
    from frontengine.user_setting.pet_game_save import HomeSaveStore
    from frontengine.user_setting.storage_session import StorageSession
    from frontengine.utils.pet_game import simulation
    from frontengine.utils.pet_game.catalog import builtin_catalog

    _refuse_media_keys()
    output.mkdir(parents=True, exist_ok=True)
    profiles, pets = _test_profiles(seed, residents)
    storage = StorageSession.open(Path.cwd())
    storage.settings.update(profiles.settings)
    storage.save_settings()
    store = HomeSaveStore(storage, builtin_catalog())
    service = view = None
    settlements, counts, pictures = [], Counter(), []
    try:
        service = HomeService(None, store, storage.profiles())
        view = HomeView()
        service.create_home("smoke", 0, 900, 40, furnish=True, seed=seed, home=_identity(seed, "home"))
        for identifier in pets:
            assert service.adopt(identifier) == "accepted"
        world = service.world
        zone = next(iter(world.zones))
        view.set_world(world, zone)
        view.resize(1280, 220)
        every = max(1, minutes // shots) if shots else None
        for minute in range(1, minutes + 1):
            simulation.advance(world, MINUTE_MS)
            for event in world.drain_events():
                counts[event["kind"]] += 1
                if event["kind"] == "settled":
                    settlements.append({key: event.get(key)
                                        for key in ("time", "resident", "task", "recipe", "coins", "transaction")})
            if every and minute % every == 0 and len(pictures) < shots:
                target = output / f"overview-{minute:04d}.png"
                view.grab().save(str(target))
                pictures.append(target.name)
        result = {
            "seed": seed, "minutes": minutes, "residents": residents,
            "fingerprint": fingerprint(world), "coins": world.ledger.coins,
            "settlements": settlements, "events": dict(sorted(counts.items())),
            "repeated_settlements": len(settlements) - len({entry["transaction"] for entry in settlements}),
            "needs": {world.residents[key].name: world.residents[key].needs for key in sorted(world.residents)},
            "screenshots": pictures, "saved": service.save_now(),
        }
    finally:
        if view is not None:
            view.close()
        if service is not None:
            assert service.shutdown()
        else:
            store.close()
        storage.close()
    (output / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def main(argv: list[str]) -> int:
    options = _arguments(argv)
    output = Path(options.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if options.native and not options.child:
        from hidden_desktop import run_on_hidden_desktop
        return run_on_hidden_desktop(__file__, *argv)
    if not options.native:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.chdir(tempfile.mkdtemp(prefix="fe-pet-game-smoke-"))
    from PySide6.QtWidgets import QApplication
    application = QApplication.instance() or QApplication([])
    result = run(output, options.seed, options.minutes, options.residents, options.shots)
    application.processEvents()
    print(json.dumps({key: result[key] for key in ("seed", "minutes", "fingerprint", "coins")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
