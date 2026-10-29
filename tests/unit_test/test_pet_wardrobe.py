"""Wardrobe transactions preserve saved identities and repairable references."""
import pytest
from PySide6.QtCore import QObject

from frontengine.show.pet.pet_profile_session import PetProfileSession
from frontengine.show.pet.wardrobe import AssetCatalog, WardrobeDraft, asset_reference
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.pet_pack.layered import load_layered_asset
from test_pet_layered import make_asset, write


@pytest.fixture
def wardrobe(tmp_path):
    body, hat = tmp_path / 'cat', tmp_path / 'hat'
    make_asset(body)
    data = make_asset(hat, garment=True)
    data['slots'] = ['head', 'neck']
    write(hat, data)
    character, garment = load_layered_asset(body), load_layered_asset(hat)
    profiles = PetProfiles({}, lambda: None)
    first, second = profiles.create('First'), profiles.create('Second')
    catalog = AssetCatalog((character, garment))
    draft = WardrobeDraft(profiles, first['id'], catalog)
    return profiles, first, second, draft, asset_reference(character), asset_reference(garment)


def test_preview_cancel_apply_and_saved_outfits_are_detached(wardrobe):
    profiles, first, second, draft, character, garment = wardrobe
    draft.choose_character(character)
    draft.equip(garment)
    outfit = draft.save_outfit('Rain')
    assert profiles.get(first['id']) == first
    assert draft.preview is not None
    draft.unequip('neck')
    assert not any(draft.appearance['equipped'].values())
    assert draft.appearance['saved_outfits'][0]['equipped']['head'] == garment
    draft.wear_outfit(outfit)
    draft.apply()
    saved = profiles.get(first['id'])
    assert saved['appearance']['equipped']['head'] == garment
    assert saved['appearance']['equipped']['neck'] == garment
    assert saved['affection'] == first['affection']
    assert profiles.get(second['id']) == second
    draft.delete_outfit(outfit)
    draft.unequip('head')
    draft.cancel()
    assert draft.preview is None
    assert draft.appearance == saved['appearance']
    reopened = WardrobeDraft(profiles, first['id'], draft.catalog)
    assert reopened.prepare_preview() is not None
    assert reopened.appearance == saved['appearance']


def test_missing_asset_is_retained_until_explicit_repair(wardrobe):
    profiles, first, _, draft, character, garment = wardrobe
    draft.choose_character(character)
    draft.equip(garment)
    draft.apply()
    before = profiles.get(first['id'])
    only_body = AssetCatalog(draft.catalog.assets('character'))
    repair = WardrobeDraft(profiles, first['id'], only_body)
    with pytest.raises(ValueError, match='Missing asset'):
        repair.prepare_preview()
    assert repair.appearance == before['appearance']
    assert profiles.get(first['id']) == before
    repair.unequip('head')
    repair.apply()
    assert not any(profiles.get(first['id'])['appearance']['equipped'].values())


def test_conflict_and_disk_failure_preserve_draft_and_live_care(wardrobe, monkeypatch):
    profiles, first, _, draft, character, garment = wardrobe
    owner = QObject()
    session = PetProfileSession(owner, first['id'], profiles)
    try:
        draft.choose_character(character)
        draft.equip(garment)
        staged = draft.appearance
        session.request('feed')
        session.advance(2)
        care = session.state()['affection']

        def fail():
            raise OSError('disk unavailable')

        with monkeypatch.context() as patch:
            patch.setattr(profiles, 'save', fail)
            with pytest.raises(OSError):
                draft.apply()
        assert draft.appearance == staged
        assert profiles.get(first['id'])['appearance'] == first['appearance']
        assert session.state()['affection'] == care
        stale = WardrobeDraft(profiles, first['id'], draft.catalog)
        draft.apply()
        assert profiles.get(first['id'])['affection'] == care
        stale.choose_character(character)
        with pytest.raises(ValueError, match='changed'):
            stale.apply()
        assert profiles.get(first['id'])['appearance'] == staged
    finally:
        session.close()


def test_saved_outfit_limit_and_invalid_names_do_not_modify_draft(wardrobe):
    _, _, _, draft, character, _ = wardrobe
    draft.choose_character(character)
    for index in range(20):
        draft.save_outfit(str(index))
    before = draft.appearance
    with pytest.raises(ValueError):
        draft.save_outfit('overflow')
    with pytest.raises(ValueError):
        draft.save_outfit('', before['saved_outfits'][0]['id'])
    assert draft.appearance == before


def test_duplicate_catalog_ids_and_partial_multislot_outfits_are_rejected(wardrobe):
    _, _, _, draft, character, garment = wardrobe
    body = draft.catalog.assets('character')[0]
    with pytest.raises(ValueError, match='Duplicate'):
        AssetCatalog((body, body))
    draft.choose_character(character)
    candidate = draft.appearance
    candidate['equipped']['head'] = garment
    with pytest.raises(ValueError, match='all its declared slots'):
        draft.catalog.prepare(candidate)


def test_apply_publishes_to_desktop_only_after_save_and_playback_pauses(wardrobe, monkeypatch):
    from PySide6.QtGui import QColor
    from frontengine.show.pet.desktop_pet import DesktopPetWidget

    profiles, first, _, draft, character, garment = wardrobe
    body = draft.catalog.assets('character')[0]
    pet = DesktopPetWidget(str(body.root / 'layer.png'), profiles=profiles,
                           profile_id=first['id'], talk=False, sit_on_windows=False)
    now = [0.0]
    pet._layered_playback.clock = lambda: now[0]
    try:
        pet.show()
        draft.choose_character(character)
        draft.equip(garment)
        assert pet._layered_playback.renderer is None
        renderer = draft.apply()
        assert pet._layered_playback.renderer is renderer
        pet._set_active_sprite('idle')
        assert pet._current_pixmap().toImage().pixelColor(2, 2) == QColor('red')
        now[0] = 0.15
        assert pet._current_pixmap().toImage().pixelColor(6, 2) == QColor('red')
        pet.hide()
        frozen = pet._current_pixmap().toImage()
        now[0] = 10.0
        assert pet._current_pixmap().toImage() == frozen
        pet.show()
        assert pet._current_pixmap().toImage() == frozen
        draft.unequip('head')

        def fail():
            raise OSError('disk unavailable')

        with monkeypatch.context() as patch:
            patch.setattr(profiles, 'save', fail)
            with pytest.raises(OSError):
                draft.apply()
        assert pet._layered_playback.renderer is renderer
        assert profiles.get(first['id'])['appearance']['equipped']['head'] == garment
        draft.apply()
        assert pet._current_pixmap().toImage().pixelColor(2, 2) == QColor('blue')
    finally:
        pet.close()


def test_hiding_pet_suspends_existing_update_timers(wardrobe):
    from frontengine.show.pet.desktop_pet import DesktopPetWidget

    profiles, first, _, draft, _, _ = wardrobe
    body = draft.catalog.assets('character')[0]
    pet = DesktopPetWidget(str(body.root / 'layer.png'), profiles=profiles,
                           profile_id=first['id'], talk=False, sit_on_windows=False)
    try:
        pet.show()
        pet.start_moving((0, 0, 800, 600))
        assert pet._timer.isActive()
        assert pet._reminder_timer.isActive()
        pet.hide()
        assert not pet._timer.isActive()
        assert not pet._reminder_timer.isActive()
        assert not pet.profile_session.care_timer.isActive()
        pet.show()
        assert pet._timer.isActive()
        assert pet._reminder_timer.isActive()
        assert pet.profile_session.care_timer.isActive()
    finally:
        pet.close()
