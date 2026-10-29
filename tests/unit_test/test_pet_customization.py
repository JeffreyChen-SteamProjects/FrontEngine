import copy

import pytest
from PySide6.QtCore import QObject

from frontengine.show.pet.pet_profile_session import PetProfileSession
from frontengine.ui.dialog.pet_customization import PetCustomizationDialog
from frontengine.user_setting.pet_profile_schema import checked_profile, presentation_defaults
from frontengine.user_setting.pet_profiles import PetProfiles


def test_old_preferences_normalize_without_mutating_source():
    profiles = PetProfiles({}, lambda: None)
    record = profiles.create('Legacy')
    del record['preferences']['presentation']
    normalized = checked_profile(record, 2)
    assert normalized['preferences']['presentation'] is None
    assert 'presentation' not in record['preferences']
    legacy = {key: record[key] for key in ('id', 'name', 'mood', 'fullness', 'affection')}
    assert checked_profile(legacy, 1)['preferences']['presentation'] is None


@pytest.mark.parametrize('changes', [
    {'size': 15}, {'size': 513}, {'size': True}, {'speed': 0}, {'speed': 21},
    {'volume': -1}, {'volume': 101}, {'behaviour': 'fly'}, {'climb': 1},
    {'sit_on_windows': None}, {'speech_bubbles': 'yes'}, {'settle_typing': 0},
    {'unknown': True},
])
def test_invalid_presentation_rejected(changes):
    profiles = PetProfiles({}, lambda: None)
    record = profiles.create()
    preferences = {**record['preferences'], 'presentation': {**presentation_defaults(), **changes}}
    with pytest.raises(ValueError):
        profiles.update(record['id'], {'preferences': preferences})
    assert profiles.get(record['id']) == record


def test_missing_presentation_fields_and_unknown_preferences_rejected():
    profiles = PetProfiles({}, lambda: None)
    record = profiles.create()
    for preferences in ({**record['preferences'], 'unknown': False},
                        {**record['preferences'], 'presentation': {'size': 128}}):
        with pytest.raises(ValueError):
            profiles.update(record['id'], {'preferences': preferences})


def test_apply_only_changes_selected_pets_preferences():
    profiles = PetProfiles({}, lambda: None)
    first, second = profiles.create('First'), profiles.create('Second')
    dialog = PetCustomizationDialog(profiles, first['id'])
    try:
        dialog.controls['use_defaults'].setChecked(False)
        dialog.controls['size'].setValue(192)
        dialog.controls['allow_throw'].setChecked(False)
        assert dialog.apply_changes()
        saved = profiles.get(first['id'])
        assert saved['preferences']['presentation']['size'] == 192
        assert not saved['preferences']['allow_throw']
        assert {key: value for key, value in saved.items() if key != 'preferences'} == {
            key: value for key, value in first.items() if key != 'preferences'}
        assert profiles.get(second['id']) == second
        assert dialog.expected == saved['preferences']
    finally:
        dialog.close()


def test_cancel_and_reset_are_staged_until_apply():
    profiles = PetProfiles({}, lambda: None)
    record = profiles.create()
    custom = {**record['preferences'], 'allow_throw': False,
              'presentation': {**presentation_defaults(), 'size': 256}}
    profiles.update(record['id'], {'preferences': custom})
    dialog = PetCustomizationDialog(profiles, record['id'])
    dialog.reset_defaults()
    assert dialog.controls['use_defaults'].isChecked()
    assert profiles.get(record['id'])['preferences'] == custom
    dialog.reject()
    assert profiles.get(record['id'])['preferences'] == custom
    another = PetCustomizationDialog(profiles, record['id'])
    try:
        another.reset_defaults()
        assert another.apply_changes()
        assert profiles.get(record['id'])['preferences']['presentation'] is None
    finally:
        another.close()


def test_conflicting_dialog_does_not_overwrite_new_preferences():
    profiles = PetProfiles({}, lambda: None)
    record = profiles.create()
    first = PetCustomizationDialog(profiles, record['id'])
    stale = PetCustomizationDialog(profiles, record['id'])
    try:
        first.controls['allow_throw'].setChecked(False)
        assert first.apply_changes()
        stale.controls['allow_social'].setChecked(False)
        assert not stale.apply_changes()
        assert stale.status.text()
        assert not stale.controls['allow_social'].isChecked()
        assert profiles.get(record['id'])['preferences']['allow_social']
    finally:
        first.close()
        stale.close()


def test_live_save_failure_keeps_runtime_source_and_draft(monkeypatch):
    profiles = PetProfiles({}, lambda: None)
    owner = QObject()
    session = PetProfileSession(owner, profiles=profiles)
    dialog = PetCustomizationDialog(profiles, session.identifier)
    before = copy.deepcopy(session.state())
    dialog.controls['allow_throw'].setChecked(False)

    def fail():
        raise OSError('disk unavailable')

    try:
        monkeypatch.setattr(profiles, 'save', fail)
        assert not dialog.apply_changes()
        assert session.state() == before
        assert profiles.get(session.identifier) == before
        assert not dialog.controls['allow_throw'].isChecked()
        assert dialog.expected == before['preferences']
        monkeypatch.setattr(profiles, 'save', lambda: None)
        assert dialog.apply_changes()
        assert not session.state()['preferences']['allow_throw']
    finally:
        monkeypatch.setattr(profiles, 'save', lambda: None)
        dialog.close()
        session.close()


def test_sprite_customization_applies_independently_and_survives_reopen(tmp_path):
    from PySide6.QtGui import QColor, QPixmap
    from frontengine.show.pet.desktop_pet import DesktopPetWidget
    from frontengine.utils.json.json_repository import JsonRepository

    path = tmp_path / 'pet.png'
    sprite = QPixmap(64, 64)
    sprite.fill(QColor('#ed6b21'))
    assert sprite.save(str(path))
    settings = {}
    disk = JsonRepository(tmp_path / 'settings.json')
    profiles = PetProfiles(settings, lambda: disk.save(settings))
    first = DesktopPetWidget(str(path), size=96, talk=False, profiles=profiles)
    second = DesktopPetWidget(str(path), size=128, talk=False, profiles=profiles)
    identifier = first.profile_session.identifier
    dialog = PetCustomizationDialog(profiles, identifier)
    try:
        assert dialog.defaults['size'] == 96
        dialog.controls['use_defaults'].setChecked(False)
        dialog.controls['size'].setValue(192)
        dialog.controls['speed'].setValue(7)
        dialog.controls['behaviour'].setCurrentIndex(1)
        dialog.controls['climb'].setChecked(False)
        assert dialog.apply_changes()
        assert first._base_size == 192
        assert first.motion.speed == 7
        assert first.motion.behaviour == 'wander'
        assert not first.motion.climb
        assert not first._talk
        assert second._base_size == 128
        assert second.profile_session.state()['preferences']['presentation'] is None
        first.close()
        reopened = PetProfiles(disk.load(), lambda: None)
        restored = DesktopPetWidget(str(path), profiles=reopened, profile_id=identifier)
        try:
            assert restored._base_size == 192
            assert restored.motion.speed == 7
            assert restored.motion.behaviour == 'wander'
            assert not restored._talk
        finally:
            restored.close()
    finally:
        dialog.close()
        first.close()
        second.close()
