"""Lifecycle defects found by the cumulative-branch review.

Each test reproduces one reported failure: a half-built pet holding its
identity, an unexpected error wedging shutdown preparation, closed widgets kept
alive by their lifetime, and overlays outside any lifetime losing geometry.
"""
import gc
import weakref
from types import SimpleNamespace

from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QWidget

from frontengine.user_setting.pet_profiles import PetProfiles


def _sprite(tmp_path):
    path = tmp_path / 'sprite.png'
    image = QPixmap(64, 64)
    image.fill(QColor('#d3a231'))
    assert image.save(str(path))
    return str(path)


def _active_sessions(profiles):
    from frontengine.show.pet import pet_profile_session
    return [session for key, session in list(pet_profile_session._ACTIVE.items())
            if key[0] == profiles.identity_key]


def test_failed_spawn_releases_the_half_built_pet_identity(tmp_path, monkeypatch, *, lifetime_factory):
    from frontengine.ui.page.pet.pet_setting_ui import PetSettingUI
    lifetime_factory()
    page = PetSettingUI(lifetime=lifetime_factory())
    controls = page.profile_controls
    controls.profiles = PetProfiles({}, lambda: None)
    controls.refresh()
    page.pet_image_path = _sprite(tmp_path)
    monkeypatch.setattr(page, '_target_geometry', lambda: None)
    original = controls.profiles.remember_sprite

    def fail(*_args):
        raise OSError('settings file is locked')

    monkeypatch.setattr(controls.profiles, 'remember_sprite', fail)
    try:
        page._spawn_pet()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        assert 'settings file is locked' in controls.status.text()
        assert page.pet_list == []
        assert _active_sessions(controls.profiles) == []
        monkeypatch.setattr(controls.profiles, 'remember_sprite', original)
        page._spawn_pet()
        assert len(page.pet_list) == 1
    finally:
        for pet in page.pet_list[:]:
            pet.close()
        page.close()


def test_refused_close_of_a_failed_spawn_keeps_the_pet_for_shutdown(tmp_path, monkeypatch, *, lifetime_factory):
    from frontengine.ui.page.pet.pet_setting_ui import PetSettingUI
    lifetime_factory()
    page = PetSettingUI(lifetime=lifetime_factory())
    controls = page.profile_controls
    controls.profiles = PetProfiles({}, lambda: None)
    controls.refresh()
    page.pet_image_path = _sprite(tmp_path)
    monkeypatch.setattr(page, '_target_geometry', lambda: None)

    def fail(*_args):
        raise OSError('settings file is locked')

    monkeypatch.setattr(controls.profiles, 'remember_sprite', fail)
    from frontengine.show.pet.pet_profile_session import PetProfileSession
    monkeypatch.setattr(PetProfileSession, 'close', lambda self: False)
    try:
        page._spawn_pet()
        # The identity could not be released, so the pet stays where shutdown looks for it.
        assert len(page.pet_list) == 1
        assert _active_sessions(controls.profiles) == [page.pet_list[0].profile_session]
    finally:
        monkeypatch.undo()
        for pet in page.pet_list[:]:
            pet.close()
        page.close()


def test_unexpected_error_while_preparing_shutdown_refuses_and_recovers(make_main_window, monkeypatch):
    from frontengine.ui.runtime_lifetime import CloseDisposition
    window = make_main_window()
    calls = []
    callback = window.lifetime.guard(lambda: calls.append('ran'))

    def broken():
        raise AttributeError('plugin page has no state')

    monkeypatch.setattr(window, '_save_page_state', broken)
    assert window.request_shutdown() is CloseDisposition.REFUSED
    assert window.lifetime.accepting
    callback()
    assert calls == ['ran']
    monkeypatch.undo()
    assert window.request_shutdown() in (CloseDisposition.DRAINING, CloseDisposition.CLOSED)


def test_closed_widgets_are_not_kept_alive_by_their_lifetime(*, lifetime_factory):
    lifetime = lifetime_factory()
    widget = QWidget()
    widget.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    widget.payload = QPixmap(256, 256)
    lifetime.adopt(widget)
    reference = weakref.ref(widget)
    widget.show()
    widget.close()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    del widget
    gc.collect()
    assert reference() is None
    assert not lifetime._roots


def test_overlay_outside_any_lifetime_still_remembers_where_it_was_left(monkeypatch):
    from frontengine.show import base_widget
    saved = []
    monkeypatch.setattr(base_widget, 'save_overlay_geometry', lambda *args: saved.append(args))
    free = base_widget.BaseWidget()
    owned = base_widget.BaseWidget()
    owned._frontengine_lifetime = SimpleNamespace(accepting=False)
    try:
        free.setGeometry(40, 50, 120, 80)
        free.remember_geometry()
        assert saved == [('BaseWidget', 40, 50, 120, 80)]
        owned.remember_geometry()
        assert len(saved) == 1
    finally:
        free.close()
        owned.close()


def test_closing_overlays_during_teardown_cannot_end_the_application_early(make_main_window, monkeypatch):
    """Closing the last visible overlay made Qt quit before the lifetime drained (tray quit)."""
    from frontengine.ui.runtime_lifetime import CloseDisposition
    window = make_main_window()
    calls = []

    class Application:
        def setQuitOnLastWindowClosed(self, enabled):
            calls.append(('quit_on_last_window', enabled))

        def exit(self, code=0):
            calls.append(('exit', code))

    clear = window._clear_overlays
    monkeypatch.setattr(window, '_clear_overlays', lambda: (calls.append(('clear_overlays',)), clear())[1])
    window.main_app = Application()
    window.hide()
    assert window.request_shutdown() in (CloseDisposition.DRAINING, CloseDisposition.CLOSED)
    assert ('quit_on_last_window', False) in calls
    assert calls.index(('quit_on_last_window', False)) < calls.index(('clear_overlays',))


def test_embedded_window_leaves_the_host_application_settings_alone(make_main_window):
    from frontengine.ui.runtime_lifetime import CloseDisposition
    window = make_main_window()
    assert window.main_app is None
    assert window.request_shutdown() in (CloseDisposition.DRAINING, CloseDisposition.CLOSED)
