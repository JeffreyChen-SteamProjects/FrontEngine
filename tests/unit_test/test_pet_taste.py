import copy

import pytest

from frontengine.utils.pet_companion.companion import CompanionState
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.ui.dialog.pet_customization import PetCustomizationDialog


@pytest.mark.parametrize('taste', [None, {}, {'favorite': 'music'},
    {'favorite': True, 'disliked': None}, {'favorite': 'hard', 'disliked': None},
    {'favorite': 'music', 'disliked': 'music'},
    {'favorite': None, 'disliked': None, 'extra': 1}])
def test_invalid_taste_preserves_profile(taste):
    profiles = PetProfiles({}, lambda: None)
    record = profiles.create()
    with pytest.raises(ValueError):
        profiles.update(record['id'], {'preferences': {**record['preferences'], 'taste': taste}})
    assert profiles.get(record['id']) == record


@pytest.mark.parametrize(('kind', 'mood', 'reaction'), [
    ('music', 44, 'food_like'), ('book', 20, 'food_dislike'), ('snack', 32, None)])
def test_taste_changes_only_completion_mood_and_temporary_reaction(kind, mood, reaction):
    pet = CompanionState({'fullness': 20, 'mood': 20, 'preferences': {
        'taste': {'favorite': 'music', 'disliked': 'book'}}})
    assert pet.request('feed', kind) == 'accepted'
    pet.advance(1)
    assert pet.mood.value == 20
    pet.advance(1)
    assert pet.mood.value == mood
    assert pet.visual_action == reaction
    assert pet.request('feed', 'feast') == 'cooldown'
    from frontengine.utils.pet_companion.stats import FOOD_EFFECTS
    assert pet.hunger.value == 20 + FOOD_EFFECTS[kind]['fullness']
    assert pet.growth.affection == FOOD_EFFECTS[kind]['affection']
    pet.advance(2)
    assert pet.visual_action is None


def test_taste_is_captured_at_start_and_cancel_has_no_reward():
    pet = CompanionState({'mood': 20, 'preferences': {'taste': {'favorite': 'music', 'disliked': None}}})
    pet.request('feed', 'music')
    pet.preferences['taste'] = {'favorite': None, 'disliked': 'music'}
    pet.advance(2)
    assert pet.mood.value == 44
    assert pet.visual_action == 'food_like'
    pet.request('cancel')
    assert pet.visual_action is None
    pet.advance(30)
    pet.request('feed', 'music')
    before = pet.snapshot()
    pet.request('cancel')
    pet.advance(2)
    assert pet.snapshot() == before


def test_dialog_taste_apply_reset_cancel_and_portable_identity(tmp_path):
    profiles = PetProfiles({}, lambda: None)
    first, other = profiles.create(), profiles.create()
    assert 'taste' not in first['preferences']
    dialog = PetCustomizationDialog(profiles, first['id'])
    try:
        for key, kind in (('favorite', 'music'), ('disliked', 'book')):
            dialog.controls[key].setCurrentIndex(dialog.controls[key].findData(kind))
        assert profiles.get(first['id']) == first
        dialog.controls['disliked'].setCurrentIndex(dialog.controls['disliked'].findData('music'))
        assert not dialog.apply_changes()
        assert dialog.status.text()
        assert profiles.get(first['id']) == first
        dialog.controls['disliked'].setCurrentIndex(dialog.controls['disliked'].findData('book'))
        assert dialog.apply_changes()
        saved = profiles.get(first['id'])
        assert saved['preferences']['taste'] == {'favorite': 'music', 'disliked': 'book'}
        dialog.reset_defaults()
        assert dialog.controls['favorite'].currentData() is None
        dialog.reject()
        assert profiles.get(first['id']) == saved
    finally:
        dialog.close()
    assert profiles.get(other['id']) == other
    cloned = profiles.create(source=saved)
    export = tmp_path / 'pet.json'
    profiles.export_profile(first['id'], export)
    imported = profiles.import_profile(export)
    assert cloned['preferences']['taste'] == imported['preferences']['taste'] == saved['preferences']['taste']
    preferences = copy.deepcopy(cloned['preferences'])
    preferences['taste']['favorite'] = 'feast'
    profiles.update(cloned['id'], {'preferences': preferences})
    assert profiles.get(first['id']) == saved
    reopened = PetCustomizationDialog(profiles, imported['id'])
    try:
        assert reopened.controls['favorite'].currentData() == 'music'
        reopened.reset_defaults()
        assert reopened.apply_changes()
        assert 'taste' not in profiles.get(imported['id'])['preferences']
    finally:
        reopened.close()


def test_live_taste_save_failure_and_midmeal_edit(monkeypatch):
    from PySide6.QtCore import QObject
    from frontengine.show.pet.pet_profile_session import PetProfileSession

    profiles = PetProfiles({}, lambda: None)
    owner = QObject()
    session = PetProfileSession(owner, profiles=profiles)
    dialog = PetCustomizationDialog(profiles, session.identifier)
    try:
        session.companion.mood.value = 20
        session.request('feed', 'music')
        before = session.state()
        dialog.controls['favorite'].setCurrentIndex(dialog.controls['favorite'].findData('music'))
        def fail():
            raise OSError('disk unavailable')
        monkeypatch.setattr(profiles, 'save', fail)
        assert not dialog.apply_changes()
        assert session.state() == before
        assert dialog.controls['favorite'].currentData() == 'music'
        monkeypatch.setattr(profiles, 'save', lambda: None)
        assert dialog.apply_changes()
        session.advance(2)
        assert session.companion.mood.value == 40
        assert session.companion.visual_action is None
        session.advance(30)
        session.request('feed', 'music')
        session.advance(2)
        assert session.companion.visual_action == 'food_like'
    finally:
        monkeypatch.setattr(profiles, 'save', lambda: None)
        dialog.close()
        session.close()
