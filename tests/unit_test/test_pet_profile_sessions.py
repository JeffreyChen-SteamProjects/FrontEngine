from PySide6.QtGui import QColor, QPixmap

from frontengine.show.pet.desktop_pet import DesktopPetWidget
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.json.json_repository import JsonRepository


def _sprite(tmp_path):
    path = tmp_path / 'sprite.png'
    image = QPixmap(64, 64)
    image.fill(QColor('#d3a231'))
    assert image.save(str(path))
    return str(path)


def test_failed_close_retains_live_pet_and_retries_without_losing_stats(tmp_path, monkeypatch):
    from frontengine.show.pet.pet_profile_session import PetProfileSession

    profiles = PetProfiles({}, lambda: None)
    pet = DesktopPetWidget(_sprite(tmp_path), talk=False, profiles=profiles)
    identifier = pet.profile_session.identifier
    try:
        pet.show()
        pet.feed()
        pet.profile_session.advance(2)
        live = pet.profile_session.state()

        def fail():
            raise OSError('disk unavailable')

        with monkeypatch.context() as patch:
            patch.setattr(profiles, 'save', fail)
            assert not pet.close()
            assert pet.isVisible()
            assert not pet.profile_session._closed
            assert pet.profile_session.timer.isActive()
            assert pet.profile_session.state() == live
            assert PetProfileSession.active(profiles, identifier) is pet.profile_session
        assert pet.close()
        assert profiles.get(identifier)['affection'] == live['affection']
        assert PetProfileSession.active(profiles, identifier) is None
        assert not pet.profile_session.timer.isActive()
    finally:
        pet.close()


def test_reward_at_affection_limit_stays_saveable(tmp_path):
    from frontengine.utils.pet_companion.stats import MAX_AFFECTION

    profiles = PetProfiles({}, lambda: None)
    record = profiles.create()
    profiles.update(record['id'], {'affection': MAX_AFFECTION - 1})
    pet = DesktopPetWidget(_sprite(tmp_path), talk=False, profiles=profiles, profile_id=record['id'])
    try:
        pet.feed()
        pet.profile_session.advance(2)
        assert pet.profile_session.state()['affection'] == MAX_AFFECTION
        assert pet.close()
        assert profiles.get(record['id'])['affection'] == MAX_AFFECTION
    finally:
        pet.close()


def test_live_pet_states_close_flush_and_resume_independently(tmp_path):
    import pytest
    settings = {}
    disk = JsonRepository(tmp_path / 'settings.json')
    profiles = PetProfiles(settings, lambda: disk.save(settings))
    path = _sprite(tmp_path)
    first = DesktopPetWidget(path, talk=False, profiles=profiles, profile_name='Amber')
    second = DesktopPetWidget(path, talk=False, profiles=profiles, profile_name='Blue')
    identifier = first.profile_session.identifier
    try:
        with pytest.raises(ValueError, match='already active'):
            DesktopPetWidget(path, profiles=profiles, profile_id=identifier)
        first.feed()
        first.profile_session.advance(2)
        second._mood.decay(15)
        second._persist_mood()
        assert first.profile_session.timer.isActive()
        first.close()
        second.close()
        assert not first.profile_session.timer.isActive()
        assert not second.profile_session.timer.isActive()
        first.close()
        reopened = PetProfiles(disk.load(), lambda: None)
        restored = DesktopPetWidget(path, talk=False, profiles=reopened, profile_id=identifier)
        try:
            assert restored._growth.affection == 5
            assert restored._mood.value == 72
            assert restored._hunger.value == 100
            assert reopened.get(second.profile_session.identifier)['mood'] == 45
            assert restored.profile_session.state()['name'] == 'Amber'
        finally:
            restored.close()
    finally:
        first.close()
        second.close()


def test_page_clone_rename_export_and_import_use_distinct_identities(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog
    from frontengine.ui.page.pet.pet_setting_ui import PetSettingUI
    page = PetSettingUI()
    controls = page.profile_controls
    controls.profiles = PetProfiles({}, lambda: None)
    controls.refresh()
    controls.name.setText('Amber')
    page.pet_image_path = _sprite(tmp_path)
    monkeypatch.setattr(page, '_target_geometry', lambda: None)
    page._spawn_pet()
    first = page.pet_list[0]
    try:
        first.feed()
        first.profile_session.advance(2)
        first.clone_requested.emit()
        clone = page.pet_list[1]
        assert clone.profile_session.identifier != first.profile_session.identifier
        assert clone._growth.affection == first._growth.affection == 5
        clone.feed()
        clone.profile_session.advance(2)
        assert clone._growth.affection == 5
        clone._hunger.decay(30)
        clone.feed()
        clone.profile_session.advance(2)
        assert first._growth.affection == 5
        assert clone._growth.affection == 10
        controls.refresh(selected=first.profile_session.identifier)
        controls.name.setText('Named pet')
        controls.rename_selected()
        assert first.profile_session.state()['name'] == 'Named pet'
        export = tmp_path / 'export.json'
        monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *_args: (str(export), ''))
        controls.export_selected()
        monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *_args: (str(export), ''))
        controls.import_save()
        imported = controls.selector.currentData()
        assert imported not in {first.profile_session.identifier, clone.profile_session.identifier}
        page._spawn_pet()
        restored = page.pet_list[2]
        assert restored.profile_session.identifier == imported
        assert restored._growth.affection == 5
        # Portable presets must not embed a local identity belonging to this machine.
        assert 'profile_id' not in page.get_state()
    finally:
        for pet in page.pet_list:
            pet.close()
        page.close()
