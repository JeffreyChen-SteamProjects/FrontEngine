"""Run only inside an isolated Linux desktop/audio session with its own fixture servers."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import wave
import numpy
from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtTest import QTest
from frontengine.utils.linux import windows
from frontengine.utils.linux.audio import PulseCapture, PulseMeter, stop_all
from frontengine.utils.linux.capabilities import x11_reason
from frontengine.utils.input_watch.input_watch_service import InputWatchService
from frontengine.utils.hotkey.hotkey_service import HotkeyService
from frontengine.utils.window_pin.window_layout import capture_layout, restore_layout
from frontengine.utils.window_pin.topology_profiles import MonitorProfileService


def wait_for(predicate, milliseconds: int = 4000) -> None:
    for _ in range(milliseconds // 25):
        QTest.qWait(25)
        if predicate():
            return
    raise AssertionError('Native condition did not complete')


def audio_probe(directory: Path) -> dict:
    """Real PulseAudio virtual source/sink; never connects to host devices or saves captured audio."""
    target = directory / 'own-input.wav'
    values = .6 * numpy.sin(2 * numpy.pi * 1000 * numpy.arange(48000 * 4) / 48000)
    with wave.open(str(target), 'wb') as stream:
        stream.setparams((1, 2, 48000, 0, 'NONE', 'not compressed'))
        stream.writeframes((values * 32767).astype('<i2').tobytes())
    capture, microphone, player = PulseCapture(), PulseMeter(microphone=True), None
    try:
        assert microphone.capture.thread is None, 'Construction must not record'
        assert capture.start()
        microphone.level()
        player = subprocess.Popen(['/usr/bin/paplay', '--device=frontengine_test', str(target)], shell=False)
        wait_for(lambda: capture.level() is not None and capture.level() > .3)
        wait_for(lambda: microphone.level() is not None and microphone.level() > .3)
        frame = capture.samples()
        peak_hz = int(numpy.argmax(abs(numpy.fft.rfft(frame))) * 48000 / len(frame))
        assert 950 <= peak_hz <= 1050
        value = {'frame_samples': len(frame), 'peak': capture.level(), 'peak_hz': peak_hz}
        wait_for(lambda: not microphone.started and not microphone.capture.running)
        wait_for(lambda: not microphone.capture.thread.is_alive())
        microphone.level()
        wait_for(lambda: microphone.capture.level() is not None and microphone.capture.level() > .3)
        value['meter_demand_stop_restart'] = True
        failed = PulseCapture('frontengine-missing-own-fixture')
        failed.start()
        wait_for(lambda: bool(failed.last_error) and not failed.running)
        assert not failed.running and 'check server' in failed.last_error
        failed.stop()
        value['missing_source_error'] = failed.last_error
        return value
    finally:
        capture.stop()
        microphone.close()
        if player:
            if player.poll() is None:
                player.terminate()
            player.wait(timeout=3)
        for session in (capture, microphone.capture):
            if session.thread:
                session.thread.join(3)
                assert not session.thread.is_alive() and session.process is None


def input_probe(handle: int) -> tuple[list, list]:
    """Deliver input only to our isolated X server and await queued native listener callbacks."""
    watch, hotkey = InputWatchService(), HotkeyService({'<ctrl>+<shift>+<f10>': 'fixture'})
    keys, actions = [], []
    watch.key_pressed.connect(keys.append, Qt.ConnectionType.QueuedConnection)
    hotkey.hotkey_triggered.connect(actions.append, Qt.ConnectionType.QueuedConnection)
    try:
        assert watch.start() and hotkey.start(), hotkey.reason
        QTest.qWait(250)
        subprocess.run(['/usr/bin/xdotool', 'windowactivate', '--sync', str(handle)], check=True, shell=False)
        subprocess.run(['/usr/bin/xdotool', 'key', 'a', 'ctrl+shift+F10'], check=True, shell=False)
        wait_for(lambda: keys and actions == ['fixture'])
        return keys, actions
    finally:
        hotkey.stop()
        watch.stop()


def own_pixel(handle: int) -> list[int]:
    """Read one pixel of our red fixture on the isolated X server, never a host desktop."""
    from Xlib import X
    rect = windows.geometry(handle)
    with windows.connection() as (_client, root):
        data = root.get_image(rect[0] + 30, rect[1] + 50, 1, 1, X.ZPixmap, 0xffffffff).data
        blue, green, red = data[:3]
        return [red, green, blue]


def opacity_probe(handle: int) -> dict:
    """Start only an owned isolated compositor; verify displayed opacity and restore it."""
    compositor = subprocess.Popen(['/usr/bin/xcompmgr', '-n'], stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL, shell=False)
    try:
        def ready():
            with windows.connection() as (client, _root):
                return bool(client.get_selection_owner(client.intern_atom('_NET_WM_CM_S0')))
        wait_for(ready)
        wait_for(lambda: own_pixel(handle)[0] == 255)
        assert windows.opacity(handle, 80), windows.last_error
        wait_for(lambda: 150 < own_pixel(handle)[0] < 250)
        faded = own_pixel(handle)
        assert windows.opacity(handle, 100), windows.last_error
        wait_for(lambda: own_pixel(handle) == [255, 0, 0])
        return {'faded_rgb': faded, 'restored_rgb': own_pixel(handle)}
    finally:
        windows.opacity(handle, 100)
        compositor.terminate()
        compositor.wait(timeout=3)


def x11_probe(directory: Path) -> dict:
    """Own Qt target, EWMH WM and own X server only; synthetic input stays inside that server."""
    target = QLabel('FrontEngine isolated X11 fixture')
    target.setWindowTitle('FrontEngine isolated X11 fixture')
    target.setStyleSheet('background:#ff0000;color:#ffffff')
    target.resize(300, 180)
    target.show()
    try:
        handle = int(target.winId())
        wait_for(lambda: any(h == handle for h, _ in windows.list_windows()))
        layout = capture_layout(lister=lambda: [(handle, target.windowTitle())])
        assert len(layout) == 1
        assert windows.move(handle, 180, 150, 320, 220), windows.last_error
        wait_for(lambda: windows.geometry(handle) == (180, 150, 320, 220))
        assert restore_layout(layout, lister=lambda: [(handle, target.windowTitle())]) == (1, 0)
        wait_for(lambda: windows.geometry(handle) == tuple(layout[0][key] for key in ('x', 'y', 'width', 'height')))
        assert windows.pin(handle, True)
        def pinned():
            with windows.connection() as (client, _root):
                window = client.create_resource_object('window', handle)
                return client.intern_atom('_NET_WM_STATE_ABOVE') in windows._property(client, window, '_NET_WM_STATE')
        wait_for(pinned)
        assert windows.pin(handle, False)
        wait_for(lambda: not pinned())
        assert not windows.opacity(handle, 80) and 'compositing manager' in windows.last_error
        opacity = opacity_probe(handle)
        assert windows.screen_rects(), windows.last_error
        keys, actions = input_probe(handle)
        profiles = MonitorProfileService(directory / 'profiles.json', lambda: [[target]])
        profiles.save_current()
        target.move(-3000, -3000)
        profiles.restore_current()
        wait_for(lambda: target.screen().availableGeometry().contains(target.geometry()))
        profiles.stop()
        return {'window_move': True, 'layout_restore': True, 'pin_and_restore': True,
                'opacity_without_compositor': 'explicit failure', 'global_input': bool(keys),
                'opacity_with_owned_compositor': opacity,
                'global_hotkey': actions, 'physical_work_areas': windows.screen_rects()}
    finally:
        target.close()


def wayland_probe(directory: Path) -> dict:
    target = QLabel('FrontEngine isolated native Wayland fixture')
    target.show()
    service = MonitorProfileService(directory / 'profiles.json', lambda: [[target]])
    try:
        QTest.qWait(150)
        assert QApplication.platformName().startswith('wayland')
        assert 'Wayland' in x11_reason() and not windows.available() and not InputWatchService.available()
        hotkey = HotkeyService({'<ctrl>+<shift>+<f10>': 'fixture'})
        assert not hotkey.start() and 'Wayland' in hotkey.reason
        try:
            service.restore_current()
        except ValueError as error:
            assert 'Wayland' in str(error)
        else:
            raise AssertionError('Wayland arbitrary positioning must not claim success')
        return {'native_qt_platform': QApplication.platformName(), 'global_input': 'explicitly unavailable',
                'arbitrary_window_control': 'explicitly unavailable', 'profile_positioning': 'explicitly unavailable'}
    finally:
        service.stop()
        target.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--isolated-fixtures', action='store_true', required=True)
    parser.add_argument('--wayland', action='store_true')
    args = parser.parse_args()
    if os.environ.get('FRONTENGINE_ISOLATED_LINUX') != '1':
        parser.error('Only run with explicitly isolated fixture servers; never against a personal desktop/audio session')
    application = QApplication([])
    application.setQuitOnLastWindowClosed(False)
    with tempfile.TemporaryDirectory() as folder:
        directory = Path(folder)
        try:
            result = wayland_probe(directory) if args.wayland else {'x11': x11_probe(directory), 'audio': audio_probe(directory)}
            print(json.dumps(result, indent=2))
            print('PASS: isolated real Linux protocol acceptance; physical audio/multiple-monitor acceptance remains separate')
        finally:
            stop_all()
            QCoreApplication.processEvents()


if __name__ == '__main__':
    main()
