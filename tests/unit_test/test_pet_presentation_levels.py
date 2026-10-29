"""Chatter frequency and animation size are separate from bubbles and volume, and optional in old saves."""
import pytest

from frontengine.show.pet import desktop_pet
from frontengine.user_setting.pet_profile_schema import checked_profile, presentation_defaults
from frontengine.user_setting.pet_profiles import PetProfiles
import test_pet_social_modes as fixtures

social_pets = fixtures.social_pets


def _presentation(**overrides):
    return {**presentation_defaults(), **overrides}


def test_schema_accepts_old_presentations_and_rejects_unknown_levels():
    record = PetProfiles({}, lambda: None).create()
    old = {key: value for key, value in presentation_defaults().items() if key not in ('chatter', 'motion')}
    checked_profile({**record, 'preferences': {**record['preferences'], 'presentation': old}})
    checked_profile({**record, 'preferences': {**record['preferences'], 'presentation': _presentation()}})
    for key, value in (('chatter', 'constantly'), ('motion', 'huge'), ('chatter', None)):
        with pytest.raises(ValueError):
            checked_profile({**record, 'preferences': {**record['preferences'],
                                                       'presentation': _presentation(**{key: value})}})


def _apply(pet, **overrides):
    before = pet.companion.preferences
    values = {**pet._presentation_defaults, **overrides}
    pet.profile_session.apply_preferences(before, {**before, 'presentation': values})


def test_chatter_level_controls_proactive_lines_only(social_pets, monkeypatch):
    _, pets = social_pets
    pet = pets[0]
    pet._talk = True
    spans = []
    monkeypatch.setattr(pet._chatter_rng, 'randint', lambda low, high: spans.append((low, high)) or low)
    _apply(pet, chatter='rare', speech_bubbles=True)
    assert spans[-1] == (40000, 90000) and pet._chatter_timer.isActive()
    _apply(pet, chatter='often', speech_bubbles=True)
    assert spans[-1] == (8000, 18000)
    _apply(pet, chatter='off', speech_bubbles=True)
    assert not pet._chatter_timer.isActive()
    pet._schedule_chatter()
    assert not pet._chatter_timer.isActive()
    assert pet.profile_session.request('greet') == 'accepted'  # responses still happen


def test_animation_size_scales_audio_pulse_and_calms_reactions(social_pets, monkeypatch):
    _, pets = social_pets
    pet = pets[0]
    seen = []
    monkeypatch.setattr(desktop_pet, 'audio_pulse_scale', lambda level, amplitude=0.3: seen.append(amplitude) or 1.0)
    pet._audio_react = True
    pet._audio_level_provider = lambda: 0.5
    for level, amplitude in (('calm', 0.12), ('normal', 0.3), ('lively', 0.45)):
        _apply(pet, motion=level)
        pet._update_audio_scale()
        assert seen[-1] == amplitude
    _apply(pet, motion='calm')
    pet.flash('land')
    pet.flash('catch')
    assert pet._flash is None
    pet.flash('peer_greet')
    assert pet._flash[0] == 'peer_greet'


def test_customization_dialog_edits_both_levels_and_fills_old_saves(social_pets):
    from frontengine.ui.dialog.pet_customization import PetCustomizationDialog
    _, pets = social_pets
    pet = pets[0]
    old = {key: value for key, value in pet._presentation_defaults.items() if key not in ('chatter', 'motion')}
    before = pet.companion.preferences
    pet.profile_session.apply_preferences(before, {**before, 'presentation': old})
    dialog = PetCustomizationDialog(pet.profile_session.profiles, pet.profile_session.identifier, parent=pet)
    try:
        assert dialog.controls['chatter'].currentData() == 'normal'
        assert dialog.controls['motion'].currentData() == 'normal'
        dialog.controls['chatter'].setCurrentIndex(dialog.controls['chatter'].findData('off'))
        dialog.controls['motion'].setCurrentIndex(dialog.controls['motion'].findData('lively'))
        assert dialog.apply_changes()
        saved = pet.companion.preferences['presentation']
        assert saved['chatter'] == 'off' and saved['motion'] == 'lively'
    finally:
        dialog.close()
