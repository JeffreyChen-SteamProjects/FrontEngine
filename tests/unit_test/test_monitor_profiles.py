"""Injected topologies prove policy only; native hotplug/DPI acceptance stays separate."""
from copy import deepcopy

import pytest
from PySide6.QtCore import Qt, QRect, QCoreApplication, QEvent
from PySide6.QtWidgets import QWidget

from frontengine.utils.window_pin.topology_profiles import (
    MonitorProfileService, ProfileRepository, topology_key, overlay_key, unique_overlays,
)
from frontengine.ui.dialog.monitor_profiles_dialog import MonitorProfilesDialog


@pytest.fixture(autouse=True)
def injected_desktop_session(monkeypatch):
    """Geometry tests run offscreen; inject native prerequisites rather than using host display access."""
    from frontengine.utils.linux import capabilities
    monkeypatch.setattr(capabilities, 'x11_reason', lambda: '')


def test_wayland_guard_rejects_restore_and_reports_auto_failure(tmp_path, monkeypatch):
    import sys
    from frontengine.utils.linux import capabilities
    first = widget('note', (10, 20, 120, 80))
    service = MonitorProfileService(tmp_path / 'profiles.json', lambda: [[first]])
    failures = []
    service.failed.connect(failures.append)
    try:
        service.save_current()
        before = first.geometry()
        monkeypatch.setattr(sys, 'platform', 'linux')
        monkeypatch.setattr(capabilities, 'x11_reason', lambda: 'Wayland arbitrary positioning is unavailable')
        with pytest.raises(ValueError, match='Wayland'):
            service.restore_current()
        service.set_enabled(True)
        service.adapt()
        assert failures == ['Wayland arbitrary positioning is unavailable']
        assert first.geometry() == before
    finally:
        cleanup(service, first)


def widget(title, rect):
    value = QWidget()
    value.setWindowFlag(Qt.WindowType.FramelessWindowHint)
    value.setWindowTitle(title)
    value.setGeometry(QRect(*rect))
    return value


def cleanup(service, *windows):
    service.stop()
    for value in windows:
        value.close()
        value.deleteLater()
        QCoreApplication.sendPostedEvents(value, QEvent.Type.DeferredDelete)


def test_round_trip_combination_resolution_primary_and_no_spawning(tmp_path):
    screens = [{'id': 'A', 'work': (0, 0, 1000, 800), 'primary': True},
               {'id': 'B', 'work': (1000, 0, 1000, 800), 'primary': False}]
    first = widget('note', (1200, 200, 160, 80))
    groups = [[first], [first]]
    service = MonitorProfileService(tmp_path / 'profiles.json', lambda: groups, screens=lambda: screens)
    try:
        assert not service.enabled and not service.timer.isActive()
        assert service.save_current() == 1
        first.move(-3000, -500)
        screens[1].update(work=(800, 0, 800, 600), primary=True, dpr=1.5)
        screens[0]['primary'] = False
        assert service.restore_current() == 1
        assert first.geometry().getRect() == (960, 150, 160, 80)
        assert not first.isVisible()
        new_service = MonitorProfileService(tmp_path / 'profiles.json', lambda: groups, screens=lambda: screens)
        assert new_service.restore_current() == 1
        new_service.stop()
        groups.clear()
        assert service.restore_current() == 0
    finally:
        cleanup(service, first)


def test_removed_monitor_clamps_and_reconnected_saved_profile_returns(tmp_path):
    screens = [{'id': 'A', 'work': (0, 0, 800, 600), 'primary': True},
               {'id': 'B', 'work': (-1000, 0, 1000, 800)}]
    first = widget('image', (-800, 200, 160, 80))
    service = MonitorProfileService(tmp_path / 'profiles.json', lambda: [[first]], screens=lambda: screens)
    try:
        service.save_current()
        second = screens.pop()
        service.restore_current()
        assert QRect(*screens[0]['work']).contains(first.geometry())
        screens.append(second)
        service.restore_current()
        assert first.geometry().getRect() == (-800, 200, 160, 80)
    finally:
        cleanup(service, first)


def test_ambiguous_duplicates_scene_follow_and_deleted_widgets_skipped(tmp_path):
    a, b, scene, followed = [widget(title, (10, 10, 120, 80)) for title in ('same', 'same', 'scene', 'follow')]
    scene.scene = object()
    groups = [[a, b, scene, followed]]
    service = MonitorProfileService(tmp_path / 'p.json', lambda: groups, excluded=lambda w: w is followed)
    try:
        assert unique_overlays(lambda: groups, lambda w: w is followed) == []
        with pytest.raises(ValueError, match='No unique'):
            service.save_current()
        b.setWindowTitle('different')
        assert service.save_current() == 2
        assert set(next(iter(service.repository.profiles.values()))) == {overlay_key(a), overlay_key(b)}
        b.setWindowTitle('same')
        a.move(-5000, -5000)
        b.move(-8000, -8000)
        assert service.restore_current() == 2
        assert a.geometry().x() >= 0 and b.geometry().x() >= 0
    finally:
        cleanup(service, a, b, scene, followed)


def test_invalid_json_bounds_and_atomic_write_failure_preserve_geometry(tmp_path, monkeypatch):
    first = widget('note', (10, 10, 120, 80))
    path = tmp_path / 'p.json'
    service = MonitorProfileService(path, lambda: [[first]])
    try:
        service.save_current()
        original = path.read_bytes()
        invalid = deepcopy(service.repository.profiles)
        entries = next(iter(invalid.values()))
        entries[overlay_key(first)]['anchor'][0] = float('nan')
        with pytest.raises(ValueError, match='bounds'):
            service.repository.save(next(iter(invalid)), entries)
        assert path.read_bytes() == original
        path.write_text('{bad', encoding='utf-8')
        service.repository = ProfileRepository(path)
        before = first.geometry()
        with pytest.raises(ValueError):
            service.restore_current()
        assert first.geometry() == before
        assert path.read_text() == '{bad'
        with pytest.raises(ValueError, match='ambiguous'):
            topology_key([{'id': 'same'}, {'id': 'same'}])
    finally:
        cleanup(service, first)


def test_explicit_enable_debounce_failure_stop_and_dialog(tmp_path):
    first = widget('note', (-2000, -2000, 120, 80))
    service = MonitorProfileService(tmp_path / 'p.json', lambda: [[first]])
    dialog = MonitorProfilesDialog(service)
    failures = []
    service.failed.connect(failures.append)
    try:
        dialog.show()
        assert not service.enabled
        assert service.save_current() == 1
        dialog.auto.setChecked(True)
        service._topology_changed()
        service._topology_changed()
        assert service.timer.isSingleShot() and service.timer.isActive()
        service.adapt()
        assert failures == []
        service.screens = lambda: []
        service.adapt()
        assert 'ambiguous' in failures[-1]
        service.stop()
        assert not service.timer.isActive() and service._connections == []
        assert not service.enabled
    finally:
        cleanup(service, dialog, first)
