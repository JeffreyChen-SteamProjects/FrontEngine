"""A refused composed close preserves the same usable home and pet objects."""
import json

import pytest
from PySide6.QtGui import QColor, QPixmap

from frontengine.show.pet.desktop_pet import DesktopPetWidget
from frontengine.show.pet.pet_profile_session import PetProfileSession
from frontengine.ui import main_ui
from frontengine.user_setting import user_setting_file
from frontengine.user_setting.pet_profiles import PetProfiles


@pytest.fixture
def running_home_and_pet(make_main_window, tmp_path):
    window = make_main_window({"language": "English", "pet_home_running": False})
    home = window.pet_home_ui
    home.create_home()
    home.service.start()
    home.desktop_check.setChecked(True)
    home.sync_strip()
    image = QPixmap(32, 32)
    image.fill(QColor("orange"))
    path = tmp_path / "pet.png"
    assert image.save(str(path))
    pet = DesktopPetWidget(str(path), profiles=home.profiles, talk=False, sit_on_windows=False)
    window.pet_setting_ui.pet_list.append(pet)
    pet.show()
    usage = window.usage_service
    usage.tracker.history = {"2026-11-05": {"test-app": 15.0}}
    usage._app_provider = lambda: "test-app"
    usage._idle_provider = lambda: 0
    usage._timer.start()
    window.show()

    return window, pet


def _refuse_save(window, monkeypatch, failure):
    def refuse(*_args):
        raise PermissionError("final save unavailable")

    if failure == "settings":
        monkeypatch.setattr(main_ui, "write_user_setting", refuse)
    elif failure == "notes":
        monkeypatch.setattr(window.widgets_setting_ui, "save_notes", refuse)
    elif failure == "session":
        monkeypatch.setitem(main_ui.user_setting_dict, "restore_last_session", True)
        monkeypatch.setattr(main_ui, "save_last_session", lambda _window: False)
    elif failure == "clipboard":
        monkeypatch.setattr(window, "_persist_clipboard", refuse)
    elif failure == "geometry":
        monkeypatch.setattr(window, "_save_window_geometry", refuse)
    else:
        monkeypatch.setattr(window.usage_service.tracker._repository, "save", refuse)


@pytest.mark.parametrize("failure", ["settings", "notes", "session", "clipboard", "geometry", "usage"])
def test_final_save_refusal_retains_home_and_pet_until_retry(running_home_and_pet, tmp_path,
                                                          monkeypatch, failure):
    window, pet = running_home_and_pet
    home, usage, session = window.pet_home_ui, window.usage_service, pet.profile_session
    strips, sessions = list(home.strip_list), dict(home.service.sessions)
    renderer, sprites = home.art, pet._sprites
    with monkeypatch.context() as patch:
        _refuse_save(window, patch, failure)
        assert window._shutdown() is False
        assert not window._shutdown_done
        assert window.isVisible() and pet.isVisible()
        assert home.strip_list == strips and all(strip.isVisible() for strip in strips)
        assert not home.art.closed
        assert home.service.sessions == sessions
        assert home.service.running
        assert usage.running
        assert home.art is renderer
        assert pet._sprites is sprites
        assert PetProfileSession.active(home.profiles, session.identifier) is session
        assert session.set_mode("work") == "accepted"
        assert home.service.run(lambda world: world.home) == home.service.world.home
        home.service._save_soon()
        assert home.service.save_now()
        assert not pet.grab().isNull()

    _assert_retry_completes(window, pet, tmp_path, monkeypatch)


def _assert_retry_completes(window, pet, tmp_path, monkeypatch):
    home, usage, session = window.pet_home_ui, window.usage_service, pet.profile_session
    saved, late_saves = [], []

    def unexpected_save(*_args):
        late_saves.append(True)
        raise PermissionError("save after final settings")

    def final_save():
        assert session.set_mode("rest") == "unsupported"
        with pytest.raises(ValueError, match="closing"):
            home.service.run(lambda world: world.home)
        with pytest.raises(ValueError, match="closing"):
            home.service.open()
        user_setting_file.write_user_setting()
        saved.append(True)
        monkeypatch.setattr(home.profiles, "save", unexpected_save)
        monkeypatch.setattr(home.service.store, "save", unexpected_save)
        monkeypatch.setattr(usage.tracker._repository, "save", unexpected_save)
        monkeypatch.setattr(window.widgets_setting_ui, "save_notes", unexpected_save)
        monkeypatch.setattr(main_ui, "save_last_session", unexpected_save)

    monkeypatch.setattr(main_ui, "write_user_setting", final_save)
    assert window._shutdown()
    assert saved == [True]
    assert not late_saves
    assert window._shutdown_done
    assert not home.service.sessions and home.art.closed
    assert PetProfileSession.active(home.profiles, session.identifier) is None
    assert session._closed
    assert session.appearance_renderer is None
    assert not session.timer.isActive()
    assert not usage.running
    restored = PetProfiles(json.loads((tmp_path / "user_setting.json").read_text(encoding="utf-8")),
                           lambda: None)
    assert restored.get(session.identifier)["mode"] == "work"
    assert home.service.store.load().world.home == home.service.world.home


def test_prepared_pet_retains_renderer_and_freezes_care_until_cancel_or_finalize(monkeypatch):
    from PySide6.QtCore import QObject

    owner = QObject()
    profiles = PetProfiles({}, lambda: None)
    session = PetProfileSession(owner, profiles=profiles)
    renderer = object()
    session.appearance_renderer = renderer
    session.resume()
    try:
        prepared = session._prepare_close()
        assert prepared is not None
        state = session.state()
        assert session.set_mode("work") == "unsupported"
        session.advance(2)
        assert session.state() == state
        assert session.appearance_renderer is renderer
        assert PetProfileSession.active(profiles, session.identifier) is session
        assert not session.close()
        prepared.cancel()
        assert session.care_timer.isActive()
        assert session.set_mode("work") == "accepted"
        prepared.finalize()
        assert not session._closed
        ready = session._prepare_close()

        def unexpected_save():
            pytest.fail("Prepared finalization must not write again")

        monkeypatch.setattr(profiles, "save", unexpected_save)
        ready.finalize()
        ready.finalize()
        assert session.close()
        assert session._closed and session.appearance_renderer is None
        assert PetProfileSession.active(profiles, session.identifier) is None
    finally:
        session.close()
