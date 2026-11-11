"""The home service: one time source, identity leases, saving and shutdown."""
import pytest

from frontengine.show.pet.pet_profile_session import PetProfileSession
from frontengine.show.pet_game.home_service import MAX_GAP_MS, HomeService
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.pet_game.catalog import builtin_catalog


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def profiles():
    return PetProfiles({}, lambda: None)


def _service(tmp_path, profiles, clock=None, write=None, *, home_store_factory) -> HomeService:
    kwargs = {} if write is None else {"write": write}
    store = home_store_factory(tmp_path, builtin_catalog(), **kwargs)
    return HomeService(None, store, profiles, clock=clock or Clock())


def _tick(service: HomeService, clock: Clock, seconds: float) -> None:
    clock.now += seconds
    service._tick()


def _furnish(service: HomeService) -> str:
    zone = next(iter(service.world.zones))
    for definition, cell in (("bed_basic", 2), ("table_basic", 7), ("desk_basic", 12)):
        assert service.run(lambda world, d=definition, c=cell: world.place(d, zone, c))[0] == "accepted"
    return zone


def test_new_home_is_saved_and_reopens(tmp_path, profiles, *, home_store_factory):
    service = _service(tmp_path, profiles, home_store_factory=home_store_factory)
    service.create_home("screen", 0, 900, 40, seed=3)
    assert (tmp_path / "pet-home.json").is_file()
    with pytest.raises(ValueError):
        service.create_home("screen", 0, 900, 40)
    assert service.store.load().status == "loaded"
    assert service.shutdown()
    other = _service(tmp_path, profiles, home_store_factory=home_store_factory)
    try:
        result = other.open()
        assert result.status == "loaded"
        assert other.world.home == service.world.home
        assert other.world.ledger.coins == 10
    finally:
        other.shutdown()


def test_time_advances_only_while_running_and_drops_long_gaps(tmp_path, profiles, *, home_store_factory):
    clock = Clock()
    service = _service(tmp_path, profiles, clock, home_store_factory=home_store_factory)
    service.create_home("screen", 0, 900, 40, seed=3)
    start = service.world.time_ms
    _tick(service, clock, 1.0)
    assert service.world.time_ms == start
    assert not service.running
    service.start()
    _tick(service, clock, 1.0)
    assert service.world.time_ms == start + 1000
    _tick(service, clock, (MAX_GAP_MS + 1) / 1000)
    assert service.world.time_ms == start + 1000
    service.pause("meeting")
    service.pause("hidden")
    assert not service.running
    service.resume("meeting")
    assert not service.running
    service.resume("hidden")
    assert service.running
    service.shutdown()


def test_adopted_pet_uses_the_world_as_its_only_clock(tmp_path, profiles, *, home_store_factory):
    clock = Clock()
    record = profiles.create("Mochi")
    service = _service(tmp_path, profiles, clock, home_store_factory=home_store_factory)
    service.create_home("screen", 0, 900, 40, seed=3)
    _furnish(service)
    assert service.adopt(record["id"]) == "accepted"
    session = PetProfileSession.active(profiles, record["id"])
    assert session is service.sessions[record["id"]]
    assert not session.care_timer.isActive()
    service.start()
    for _ in range(300):
        _tick(service, clock, 0.2)
    resident = service.world.residents[record["id"]]
    assert resident.needs != {"energy": 70, "fullness": 70, "mood": 60}
    assert service.save_now()
    saved = profiles.get(record["id"])
    assert (saved["energy"], saved["fullness"], saved["mood"]) == (
        resident.needs["energy"], resident.needs["fullness"], resident.needs["mood"])
    assert service.shutdown()
    assert PetProfileSession.active(profiles, record["id"]) is None


def test_live_pet_cannot_move_in_twice(tmp_path, profiles, *, home_store_factory):
    record = profiles.create("Mochi")
    live = PetProfileSession(None, record["id"], profiles)
    service = _service(tmp_path, profiles, home_store_factory=home_store_factory)
    service.create_home("screen", 0, 900, 40, seed=3)
    assert service.adopt(record["id"]) == "active_elsewhere"
    assert record["id"] not in service.world.residents
    live.close()
    assert service.adopt(record["id"]) == "accepted"
    assert service.adopt(record["id"]) == "duplicate"
    service.shutdown()


def test_resident_live_elsewhere_is_away_until_released(tmp_path, profiles, *, home_store_factory):
    clock = Clock()
    record = profiles.create("Mochi")
    service = _service(tmp_path, profiles, clock, home_store_factory=home_store_factory)
    service.create_home("screen", 0, 900, 40, seed=3)
    service.adopt(record["id"])
    assert service.shutdown()
    live = PetProfileSession(None, record["id"], profiles)
    reopened = _service(tmp_path, profiles, clock, home_store_factory=home_store_factory)
    reopened.open()
    resident = reopened.world.residents[record["id"]]
    assert resident.away
    assert not resident.parked
    before = dict(resident.needs), resident.x_milli
    reopened.start()
    for _ in range(100):
        _tick(reopened, clock, 0.2)
    assert before == (dict(resident.needs), resident.x_milli)
    live.close()
    assert reopened.retry_leases() == [record["id"]]
    assert not resident.away
    reopened.shutdown()


def test_failed_save_keeps_memory_and_retries(tmp_path, profiles, *, home_store_factory):
    service = _service(tmp_path, profiles, home_store_factory=home_store_factory)
    service.create_home("screen", 0, 900, 40, seed=3)
    failures = []

    def fail(path, data):
        raise OSError("disk full")

    original_write = service.store._write
    service.store._write = fail
    service.save_failed.connect(failures.append)
    assert service.run(lambda world: world.buy("plant_pot", "b1")) == "insufficient_coins"
    assert not service.save_now()
    assert failures == ["disk full"]
    assert service.save_timer.isActive()
    assert service.world.ledger.coins == 10
    assert not service.shutdown()
    service.store._write = original_write
    assert service.shutdown()


def test_shutdown_pauses_work_without_paying_partial_units(tmp_path, profiles, *, home_store_factory):
    clock = Clock()
    record = profiles.create("Mochi")
    service = _service(tmp_path, profiles, clock, home_store_factory=home_store_factory)
    service.create_home("screen", 0, 900, 40, seed=3)
    service.world.automatic = False    # only the one letter below, no jobs or rewards taken by themselves
    _furnish(service)
    service.adopt(record["id"])
    service.run(lambda world: world.create_task("letter", record["id"]))
    service.start()
    for _ in range(200):
        _tick(service, clock, 0.2)
    assert service.shutdown()
    reopened = _service(tmp_path, profiles, home_store_factory=home_store_factory)
    world = reopened.open().world
    task = next(iter(world.tasks.values()))
    assert task.state == "paused"
    assert task.progress_ms > 0
    assert world.ledger.coins == 10
    reopened.shutdown()


def test_release_returns_care_values_to_the_profile(tmp_path, profiles, *, home_store_factory):
    clock = Clock()
    record = profiles.create("Mochi")
    service = _service(tmp_path, profiles, clock, home_store_factory=home_store_factory)
    service.create_home("screen", 0, 900, 40, seed=3)
    service.adopt(record["id"])
    service.world.residents[record["id"]].needs["mood"] = 12
    assert service.release(record["id"]) == "accepted"
    assert profiles.get(record["id"])["mood"] == 12
    assert PetProfileSession.active(profiles, record["id"]) is None
    service.shutdown()


def _wait(condition, timeout: float = 5.0) -> None:
    import time

    from PySide6.QtCore import QCoreApplication
    deadline = time.monotonic() + timeout
    while not condition():
        QCoreApplication.processEvents()
        assert time.monotonic() < deadline, "timed out"
        time.sleep(0.005)


def test_routine_saves_run_on_one_worker_and_coalesce(tmp_path, profiles, *, home_store_factory):
    import threading
    from concurrent.futures import ThreadPoolExecutor

    gate = threading.Event()
    threads, writes = set(), []
    store = home_store_factory(tmp_path, builtin_catalog())
    original = store._write

    def slow_write(path, data):
        gate.wait(5)
        threads.add(threading.current_thread().name)
        writes.append(path.name)
        original(path, data)

    service = HomeService(None, store, profiles, clock=Clock(),
                          executor=ThreadPoolExecutor(1, thread_name_prefix="home-save"))
    service.create_home("screen", 0, 900, 40, seed=3)     # synchronous first save
    store._write = slow_write
    saved = []
    service.saved.connect(lambda: saved.append(threading.current_thread().name))
    service.run(lambda world: world.ledger.apply("gift", "test", 5))
    service._save_soon()
    service.run(lambda world: world.ledger.apply("gift2", "test", 5))
    service._save_soon()          # coalesced behind the first write
    gate.set()
    _wait(lambda: len(saved) == 2)
    assert threads == {next(iter(threads))}
    assert next(iter(threads)).startswith("home-save")
    assert saved == [threading.current_thread().name] * 2
    reloaded = store.load().world
    assert reloaded.ledger.coins == 20
    assert service.shutdown()


def test_background_failure_is_reported_on_the_gui_thread(tmp_path, profiles, *, home_store_factory):
    import threading
    from concurrent.futures import ThreadPoolExecutor

    store = home_store_factory(tmp_path, builtin_catalog())
    service = HomeService(None, store, profiles, clock=Clock(), executor=ThreadPoolExecutor(1))
    service.create_home("screen", 0, 900, 40, seed=3)

    def fail(path, data):
        raise OSError("disk full")

    original_write = store._write
    store._write = fail
    failures = []
    service.save_failed.connect(lambda text: failures.append((text, threading.current_thread().name)))
    service._save_soon()
    _wait(lambda: failures)
    assert failures == [("disk full", threading.current_thread().name)]
    assert service.save_timer.isActive()
    store._write = original_write
    assert service.shutdown()
