"""Manual-dispatch ownership, initialization rollback and idempotent shutdown."""
import ctypes as c

import pytest

from frontengine.utils.steam.steam_runtime import (
    APP_ID, BASE_FUNCTIONS, UGC_FUNCTIONS, CallbackMessage, SteamRuntime,
)


class Function:
    def __init__(self, value=0):
        self.value = value
        self.calls = []

    def __call__(self, *arguments):
        self.calls.append(arguments)
        return self.value(*arguments) if callable(self.value) else self.value


class Library:
    def __init__(self):
        for name in BASE_FUNCTIONS:
            setattr(self, name, Function())
        for name in UGC_FUNCTIONS:
            setattr(self, 'SteamAPI_ISteamUGC_' + name, Function())
        for name in ('SteamAPI_SteamUGC_v021', 'SteamAPI_SteamUser_v023',
                     'SteamAPI_SteamUtils_v011', 'SteamAPI_GetHSteamPipe'):
            getattr(self, name).value = 1
        self.SteamAPI_ISteamUtils_GetAppID.value = APP_ID
        self.SteamAPI_ISteamUser_GetSteamID.value = 123
        self.SteamAPI_ISteamUser_BLoggedOn.value = True


@pytest.fixture
def session(tmp_path, monkeypatch):
    monkeypatch.setattr('frontengine.utils.steam.steam_runtime.sys.platform', 'win32')
    path = tmp_path / 'steam_api64.dll'
    path.touch()
    library = Library()
    runtime = SteamRuntime(path, loader=lambda *args, **kwargs: library)
    return runtime, library


def test_construction_is_lazy_and_shutdown_occurs_once(session):
    runtime, library = session
    assert not library.SteamAPI_InitFlat.calls
    assert runtime.initialize()
    assert runtime.initialize()
    assert len(library.SteamAPI_InitFlat.calls) == 1
    runtime.shutdown()
    runtime.shutdown()
    assert len(library.SteamAPI_Shutdown.calls) == 1


def test_service_stops_timer_before_native_shutdown():
    from frontengine.utils.workshop.workshop_service import WorkshopService
    class Backend:
        reason = ''
        def initialize(self):
            return True
        def shutdown(self):
            assert not service.timer.isActive()
        def poll(self):
            return []
    service = WorkshopService(backend=Backend())
    assert service.start()
    assert service.timer.isActive()
    service.stop()
    assert not service.timer.isActive()


def test_wrong_app_rolls_back_native_initialization(session):
    runtime, library = session
    library.SteamAPI_ISteamUtils_GetAppID.value = 480
    assert not runtime.initialize()
    assert 'another application' in runtime.reason
    assert len(library.SteamAPI_Shutdown.calls) == 1


def test_failed_init_does_not_shutdown_uninitialized_library(session):
    runtime, library = session
    library.SteamAPI_InitFlat.value = 1
    assert not runtime.initialize()
    assert not library.SteamAPI_Shutdown.calls


def test_invalid_callback_is_freed_even_when_decoding_fails(session):
    runtime, library = session
    assert runtime.initialize()
    def callback(pipe, pointer):
        message = c.cast(pointer, c.POINTER(CallbackMessage)).contents
        message.size = -1
        return True
    library.SteamAPI_ManualDispatch_GetNextCallback.value = callback
    with pytest.raises(ValueError, match='callback size'):
        runtime.poll()
    assert len(library.SteamAPI_ManualDispatch_FreeLastCallback.calls) == 1


def test_poll_copies_data_and_bounds_each_batch(session):
    runtime, library = session
    assert runtime.initialize()
    payload = c.create_string_buffer(b'payload')
    def callback(pipe, pointer):
        message = c.cast(pointer, c.POINTER(CallbackMessage)).contents
        message.callback, message.size = 3405, 7
        message.data = c.cast(payload, c.c_void_p).value
        return True
    library.SteamAPI_ManualDispatch_GetNextCallback.value = callback
    events = runtime.poll(limit=3)
    assert len(events) == 3
    payload.value = b'changed'
    assert events[0].payload == b'payload'
    assert len(library.SteamAPI_ManualDispatch_FreeLastCallback.calls) == 3
    runtime.shutdown()
