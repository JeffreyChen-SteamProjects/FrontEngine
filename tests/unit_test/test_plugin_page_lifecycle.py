"""Trusted API example participates in batches, preset rollback and final cleanup."""
from types import SimpleNamespace
from threading import Event, Thread

import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from frontengine.ui.plugin_pages import attach_page, shutdown_pages
from frontengine.ui.menu.preset_menu import _collect_state, _apply_state, apply_state_transaction
from frontengine.ui.main_ui import FrontEngineMainUI
from frontengine.utils.plugins.plugin_manifest import read_manifest, API_VERSION
from frontengine.utils.shutdown_barrier import ShutdownBarrier
from examples.plugins.clock.plugin import ClockPage


def test_example_manifest_api_and_real_registered_close_all(centre):
    from pathlib import Path
    manifest = read_manifest(Path(__file__).resolve().parents[2] / 'examples/plugins/clock/plugin.py')
    assert manifest.permissions == ('ui',) and not manifest.legacy and API_VERSION == 1
    page = attach_page('Example clock', ClockPage, centre)
    try:
        page.open_clock()
        overlay = page.overlay_widgets[0]
        assert overlay in centre.all_overlays() and overlay.timer.isActive()
        centre.hide_all()
        assert not overlay.timer.isActive()
        centre.show_all()
        assert overlay.timer.isActive()
        centre.clear_all()
        assert not overlay.timer.isActive() and not page.overlay_widgets
        page.open_clock()
        assert len(page.overlay_widgets) == 1
    finally:
        page.shutdown()
        page.close()
        page.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.fixture
def centre():
    from frontengine.ui.page.control_center.control_center_ui import ControlCenterUI
    pages = {name: SimpleNamespace(**{field: []}) for name, field in (
        ('video_setting_ui', 'video_widget_list'), ('image_setting_ui', 'image_widget_list'),
        ('web_setting_ui', 'web_widget_list'), ('gif_setting_ui', 'gif_widget_list'),
        ('sound_player_setting_ui', 'sound_widget_list'), ('text_setting_ui', 'text_widget_list'),
        ('particle_setting_ui', 'particle_list'))}
    pages['scene_setting_ui'] = SimpleNamespace(close_scene=lambda: None)
    value = ControlCenterUI(**pages, redirect_output=False)
    yield value
    value.close()
    value.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_plugin_state_namespaced_round_trip_and_transactional_rollback():
    page, broken = ClockPage(), ClockPage()
    ui = SimpleNamespace(plugin_pages={'clock': page, 'broken': broken})
    try:
        page.caption.setText('Current')
        state = _collect_state(ui)
        assert state['plugin:clock'] == {'caption': 'Current'}
        _apply_state(ui, {'plugin:clock': {'caption': 'Restored'}})
        assert page.caption.text() == 'Restored'
        with pytest.raises(RuntimeError, match='caption'):
            apply_state_transaction(ui, {'plugin:clock': {'caption': 'Temporary'},
                                         'plugin:broken': {'caption': 42}})
        assert page.caption.text() == 'Restored'
        with pytest.raises(ValueError, match='Invalid preset'):
            apply_state_transaction(ui, {'plugin:clock': []})
    finally:
        shutdown_pages(ui)
        page.deleteLater()
        broken.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_main_shutdown_uses_every_registered_source_deduplicated_before_clearing(centre):
    calls, cleaned, extra = [], [], []
    class Sentinel:
        def close(self):
            calls.append('close')
            assert extra, 'Lists must stay populated until closeEvent cleanup runs'
    sentinel = Sentinel()
    extra.append(sentinel)
    centre.video_setting_ui.video_widget_list.append(sentinel)
    centre.register_overlay_source(lambda: extra)
    centre.register_cleanup(lambda: cleaned.append('cleanup'))
    ui = SimpleNamespace(control_center_ui=centre,
                         wallpaper_setting_ui=SimpleNamespace(wallpaper_widgets={'screen': sentinel}))
    FrontEngineMainUI._clear_overlays(ui)
    assert calls == ['close'] and cleaned == ['cleanup']
    assert extra == [] and not ui.wallpaper_setting_ui.wallpaper_widgets


def test_shutdown_barrier_keeps_gui_running_and_finishes_once_after_worker_release():
    waiting, finished, ticks = Event(), [], []
    worker = Thread(target=waiting.wait)
    worker.start()
    barrier = ShutdownBarrier(worker.is_alive, lambda: finished.append(True))
    try:
        barrier.start()
        barrier.poll()
        QCoreApplication.processEvents()
        ticks.append(True)
        assert ticks and not finished and barrier.timer.isActive()
        waiting.set()
        worker.join(timeout=1)
        assert not worker.is_alive()
        barrier.poll()
        barrier.poll()
        assert finished == [True] and not barrier.timer.isActive()
    finally:
        waiting.set()
        worker.join(timeout=1)
        barrier.timer.stop()
        barrier.deleteLater()
