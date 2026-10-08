"""Injected process and session policy; real Linux acceptance is a separate script."""
from threading import Event
from time import monotonic
import numpy
import pytest

from frontengine.utils.linux.capabilities import x11_reason
from frontengine.utils.linux.audio import PulseCapture, PulseMeter
from frontengine.ui.dialog.platform_capabilities_dialog import PlatformCapabilitiesDialog


def test_x11_wayland_and_headless_reasons_do_not_claim_xwayland_global_support():
    assert x11_reason(platform='linux', environment={'DISPLAY': ':9'}) == ''
    assert 'DISPLAY' in x11_reason(platform='linux', environment={})
    assert 'Wayland' in x11_reason(platform='linux', environment={'DISPLAY': ':9', 'WAYLAND_DISPLAY': 'wayland-0'})
    assert 'Wayland' in x11_reason(platform='linux', environment={'QT_QPA_PLATFORM': 'wayland'})
    assert 'requires Linux' in x11_reason(platform='win32', environment={})


class Process:
    def __init__(self):
        self.killed, self.delivered, self.closed = Event(), Event(), False
        self.stdout, self.sent = self, False
    def read(self, size):
        if not self.sent:
            self.sent = True
            return numpy.array([.5, float('nan'), float('inf'), 2] * 512, dtype='<f4').tobytes()
        self.delivered.set()
        self.killed.wait(3)
        return b''
    def kill(self):
        self.killed.set()
    def poll(self):
        return -9 if self.killed.is_set() else None
    def wait(self):
        return -9
    def close(self):
        self.closed = True


def test_bounded_float_frame_sanitizes_and_stop_reaps_only_owned_process():
    process, commands = Process(), []
    def launch(argv, **kwargs):
        commands.append((argv, kwargs))
        return process
    capture = PulseCapture(launcher=launch, executable=lambda: '/usr/bin/parec')
    try:
        assert capture.start() and process.delivered.wait(1)
        samples = capture.samples()
        assert len(samples) == 2048 and numpy.isfinite(samples).all() and samples.max() == 1
        assert commands[0][0][-1] == '--device=@DEFAULT_MONITOR@'
        assert commands[0][1]['shell'] is False
        start = monotonic()
        capture.stop()
        assert monotonic() - start < .5
        capture.thread.join(1)
        assert not capture.thread.is_alive() and process.closed
        assert len(capture.samples()) == 0 and capture.level() is None
    finally:
        capture.stop()
        capture.thread.join(1)


def test_stop_during_spawn_has_no_late_child_and_connection_error_is_visible():
    entered, release = Event(), Event()
    process = Process()
    def launch(*args, **kwargs):
        entered.set()
        release.wait(2)
        return process
    capture = PulseCapture(launcher=launch, executable=lambda: '/usr/bin/parec')
    try:
        capture.start()
        assert entered.wait(1)
        capture.stop()
        release.set()
        capture.thread.join(1)
        assert process.killed.is_set() and not capture.running and not capture.thread.is_alive()
    finally:
        release.set()
        capture.stop()
        capture.thread.join(1)
    missing = PulseCapture(executable=lambda: None)
    assert not missing.start() and 'Install' in missing.last_error
    failed = PulseCapture(launcher=lambda *a, **k: (_ for _ in ()).throw(OSError('permission denied')),
                          executable=lambda: '/usr/bin/parec')
    failed.start()
    failed.thread.join(1)
    assert not failed.running and failed.last_error == 'permission denied'


def test_lazy_meter_construction_never_launches_disabled_audio(monkeypatch):
    calls = []
    monkeypatch.setattr(PulseCapture, 'start', lambda self: calls.append(True))
    meter = PulseMeter(microphone=True)
    assert not calls and meter.capture.device == '@DEFAULT_SOURCE@'
    assert meter.level() is None
    meter.level()
    assert calls == [True]
    meter.close()
    meter.level()
    assert calls == [True]
    with pytest.raises(ValueError):
        PulseCapture('bad\0source')


def test_meter_stops_after_demand_ends_and_can_restart_on_explicit_sampling(monkeypatch):
    starts, stops = [], []
    monkeypatch.setattr(PulseCapture, 'start', lambda self: starts.append(True))
    monkeypatch.setattr(PulseCapture, 'stop', lambda self: stops.append(True))
    meter = PulseMeter()
    try:
        meter.level()
        meter.last_demand = monotonic() - 2
        meter._expire()
        assert stops == [True] and not meter.idle_timer.isActive() and not meter.started
        meter.level()
        assert starts == [True, True] and meter.idle_timer.isActive()
    finally:
        meter.close()


def test_platform_dialog_read_only_and_shows_original_failure_reason():
    calls = []
    def provider():
        calls.append(True)
        return [('system_audio', False, 'permission denied: native source')]
    dialog = PlatformCapabilitiesDialog(provider=provider)
    try:
        assert dialog.table.item(0, 2).text() == 'permission denied: native source'
        dialog.refresh()
        assert len(calls) == 2
    finally:
        dialog.close()
        dialog.deleteLater()
