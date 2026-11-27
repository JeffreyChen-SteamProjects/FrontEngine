"""The pet home benchmark runs against a real storage session and releases it (benchmarks/pet_home.py)."""
from PySide6.QtWidgets import QApplication

from benchmarks import pet_home
from frontengine.user_setting.pet_game_save import FILE_NAMES
from frontengine.user_setting.storage_session import StorageSession

TINY = pet_home.Sizes(warm_steps=2, measure_steps=3, encodes=2, commands=4, frames=2, long_marks=(1, 2, 3))
LOAD_KEYS = {"residents", "furniture", "world_step", "operation_feedback", "save_encode", "strip_frame",
             "game_data_mb", "save_bytes"}


def test_a_minimal_run_returns_a_complete_report():
    app = QApplication.instance() or QApplication([])
    report = pet_home.collect(app, loads=((1, 2),), long_load=(1, 2), sizes=TINY)
    assert set(report) == {"machine", "budget", "loads", "long", "within_budget", "investigate_memory_growth"}
    (load,) = report["loads"]
    assert set(load) == LOAD_KEYS and load["residents"] == 1 and load["save_bytes"] > 0
    assert load["operation_feedback"]["samples"] == 4 and load["strip_frame"]["samples"] == 2
    assert set(report["within_budget"]) == {"tick_p95_ms", "feedback_p95_ms", "game_memory_mb"}
    assert {"at_10_min", "at_2_hours", "at_4_hours", "memory_growth_percent"} <= set(report["long"])


def test_a_load_closes_its_service_store_and_session(tmp_path):
    pet_home.measure_load(1, 2, tmp_path, TINY)
    assert (tmp_path / FILE_NAMES["manage"]).is_file()  # the service saved on shutdown
    successor = StorageSession.open(tmp_path)  # the directory lock was released
    successor.close()
