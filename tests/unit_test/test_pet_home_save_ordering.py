"""Background write completion and blocking saves can arrive in either order."""
import json
from concurrent.futures import Executor, Future

import pytest
from PySide6.QtCore import QCoreApplication

from frontengine.show.pet_game.home_service import HomeService
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.pet_game.catalog import builtin_catalog


class ControlledWriter(Executor):
    def __init__(self):
        self.jobs = []

    def submit(self, function, *args, **kwargs):
        future = Future()
        self.jobs.append((future, function, args, kwargs))
        return future

    def finish(self, index):
        future, function, args, kwargs = self.jobs[index]
        future.set_running_or_notify_cancel()
        try:
            result = function(*args, **kwargs)
        except Exception as error:
            future.set_exception(error)
        else:
            future.set_result(result)


@pytest.fixture
def service(tmp_path, *, home_store_factory):
    writer = ControlledWriter()
    home = HomeService(None, home_store_factory(tmp_path, builtin_catalog()),
                       PetProfiles({}, lambda: None), executor=writer)
    original_write = home.store._write
    home.create_home('screen', 0, 900, 40, seed=3)
    yield home, writer
    home.store._write = original_write
    for index, job in enumerate(writer.jobs):
        if not job[0].done():
            writer.finish(index)
    assert home.shutdown()
    home.deleteLater()


@pytest.mark.parametrize('operation', ['save', 'shutdown', 'switch'])
def test_failed_worker_is_reported_before_its_queued_notification(service, operation):
    home, writer = service

    def full_disk(path, data):
        raise OSError('disk full')

    home.store._write = full_disk
    failures = []
    home.save_failed.connect(failures.append)
    home._save_soon()
    writer.finish(0)
    if operation == 'save':
        result = home.save_now()
        assert result is False
    elif operation == 'shutdown':
        assert home.shutdown() is False
    else:
        assert home.switch_mode('sandbox') is None
        assert home.mode == 'manage'
    assert failures
    assert 'disk full' in failures[-1]


def test_old_completion_cannot_allow_two_unfinished_writes(service):
    home, writer = service
    home._save_soon()
    writer.finish(0)
    assert home.save_now()
    home.schedule_save()
    home._save_soon()
    assert sum(not job[0].done() for job in writer.jobs) == 1
    QCoreApplication.processEvents()
    home._save_soon()
    assert sum(not job[0].done() for job in writer.jobs) == 1


def test_background_save_retries_profiles_before_announcing_success(service, monkeypatch):
    home, writer = service
    identifiers = sorted(home.profiles.create(name)["id"] for name in ("First", "Second"))
    for identifier in identifiers:
        assert home.adopt(identifier) == "accepted"
        home.world.residents[identifier].needs["energy"] -= 10
    failures, saved, attempts = [], [], []
    home.save_failed.connect(failures.append)
    home.saved.connect(lambda: saved.append(True))

    def fail_first_profile():
        attempts.append(True)
        if len(attempts) == 1:
            raise PermissionError("profile disk unavailable")

    try:
        with monkeypatch.context() as patch:
            patch.setattr(home.profiles, "save", fail_first_profile)
            home._save_soon()
            writer.finish(0)
            QCoreApplication.processEvents()
            assert failures
            assert not saved
            assert len(attempts) == 2
            first, second = identifiers
            assert home.profiles.get(first)["energy"] != home.world.residents[first].needs["energy"]
            assert home.profiles.get(second)["energy"] == home.world.residents[second].needs["energy"]
            assert home.save_timer.isActive()
            home.save_timer.timeout.emit()
            writer.finish(1)
            QCoreApplication.processEvents()
            assert saved == [True]
            assert home.profiles.get(first)["energy"] == home.world.residents[first].needs["energy"]
            assert not home.running
    finally:
        home.shutdown()


def _busy_home(home):
    """One pet wandering, one working at a reserved planter on an open task."""
    from frontengine.utils.pet_game.behaviour import start
    world = home.world
    world.automatic = False
    zone = next(iter(world.zones))
    world.ledger.apply("gift", "test", 1000)
    assert world.buy("planter", "buy-planter") == "accepted"
    status, planter = world.place("planter", zone, 18)
    assert status == "accepted"
    wanderer, worker = sorted(home.profiles.create(name)["id"] for name in ("Wanderer", "Worker"))
    for identifier in (wanderer, worker):
        assert home.adopt(identifier) == "accepted"
    task = world.create_task("herbs", worker)[1]
    world.tasks[task].state = "working"
    start(world, world.residents[wanderer], "wander", "free")
    start(world, world.residents[worker], "work", "task", furniture=planter, point=0, task=task)
    world.drain_events()
    return world, planter, task


def _world_state(world, planter, task):
    activities = {key: resident.activity for key, resident in world.residents.items()}
    return activities, dict(world.furniture[planter].users), world.tasks[task].state


def test_failed_mode_switch_save_leaves_activities_jobs_and_reservations(service):
    from frontengine.utils.pet_game import snapshot
    home, _writer = service
    world, planter, task = _busy_home(home)
    before = (snapshot.to_dict(world), _world_state(world, planter, task))
    assert all(state is not None for state in before[1][0].values()) and before[1][1]

    def full_disk(path, data):
        raise OSError("disk full")

    home.store._write = full_disk
    assert home.switch_mode("sandbox") is None
    assert home.mode == "manage" and home.world is world
    assert (snapshot.to_dict(world), _world_state(world, planter, task)) == before
    assert not world.drain_events()
    assert sorted(home.sessions) == sorted(world.residents)


def test_mode_switch_saves_what_cancelling_the_live_world_gives(service):
    from frontengine.show.pet_game import home_service
    from frontengine.utils.pet_game import snapshot
    home, _writer = service
    world, planter, task = _busy_home(home)
    departing = home_service._detached_copy(world)
    home_service._cancel_all(departing, "mode_switch")
    home_service._cancel_all(world, "mode_switch")
    assert snapshot.to_dict(departing) == snapshot.to_dict(world)
    assert world.residents and all(resident.activity is None for resident in world.residents.values())
    assert world.furniture[planter].users == {} and world.tasks[task].state == "paused"


def test_mode_switch_cancels_live_activities_once_the_save_succeeds(service):
    from frontengine.utils.pet_game import snapshot
    home, _writer = service
    world, planter, task = _busy_home(home)
    path = home.store.path
    assert home.switch_mode("sandbox") is not None and home.mode == "sandbox"
    assert all(resident.activity is None for resident in world.residents.values())
    assert world.furniture[planter].users == {}
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved == snapshot.to_dict(world)
    assert next(item for item in saved["tasks"] if item["id"] == task)["state"] == "paused"
