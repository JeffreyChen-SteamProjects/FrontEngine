"""Background write completion and blocking saves can arrive in either order."""
from concurrent.futures import Executor, Future

import pytest
from PySide6.QtCore import QCoreApplication

from frontengine.show.pet_game.home_service import HomeService
from frontengine.user_setting.pet_game_save import HomeSaveStore
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
def service(tmp_path):
    writer = ControlledWriter()
    home = HomeService(None, HomeSaveStore(tmp_path, builtin_catalog()),
                       PetProfiles({}, lambda: None), executor=writer)
    home.create_home('screen', 0, 900, 40, seed=3)
    yield home, writer
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
    assert failures and 'disk full' in failures[-1]


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
