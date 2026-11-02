"""The background smoke entry replays exactly for a seed, records settlements and screenshots,
and refuses to press a real media key."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "integration"))
import pet_game_smoke  # noqa: E402

from frontengine.utils.media_keys import media_keys  # noqa: E402


@pytest.fixture
def smoke(tmp_path, monkeypatch):
    monkeypatch.setattr(media_keys, "send_media_key", media_keys.send_media_key)   # restored afterwards

    def run(name, seed=5, minutes=90, residents=2, shots=2):
        work = tmp_path / name / "work"
        work.mkdir(parents=True)
        monkeypatch.chdir(work)
        return pet_game_smoke.run(tmp_path / name / "out", seed, minutes, residents, shots)
    return run


def test_the_same_seed_replays_to_the_same_home(smoke, tmp_path):
    first, second = smoke("a"), smoke("b")
    assert first["fingerprint"] == second["fingerprint"]
    assert first["settlements"] == second["settlements"]
    assert first["settlements"], "an hour and a half of work settles something"
    assert first["repeated_settlements"] == 0
    assert first["saved"] is True
    written = json.loads((tmp_path / "a" / "out" / "result.json").read_text(encoding="utf-8"))
    assert written["fingerprint"] == first["fingerprint"]
    assert [path.name for path in sorted((tmp_path / "a" / "out").glob("overview-*.png"))] == first["screenshots"]
    assert len(first["screenshots"]) == 2


def test_another_seed_lives_differently(smoke):
    assert smoke("a", seed=5)["fingerprint"] != smoke("b", seed=6)["fingerprint"]


def test_media_keys_are_refused_during_a_run(smoke):
    smoke("a", minutes=1, shots=0)
    with pytest.raises(pet_game_smoke.RefusedOutsideEffect):
        media_keys.send_media_key("play_pause")


def test_arguments_are_bounded():
    assert pet_game_smoke._arguments(["out"]).minutes == 60
    for bad in (["out", "--minutes", "0"], ["out", "--residents", "9"], ["out", "--shots", "99"]):
        with pytest.raises(SystemExit):
            pet_game_smoke._arguments(bad)
