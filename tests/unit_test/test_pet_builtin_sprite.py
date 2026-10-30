"""The Pet page's built-in character starts sprite pets dressed as that character."""
from PySide6.QtCore import QCoreApplication, QEvent, QThreadPool

from frontengine.show.pet.desktop_pet import DesktopPetWidget
from frontengine.user_setting.pet_profiles import PetProfiles

REFERENCE = {'id': 'inkside-pip', 'version': '1'}


def _ready_page(tmp_path, monkeypatch):
    from frontengine.ui.page.pet.pet_setting_ui import PetSettingUI
    monkeypatch.chdir(tmp_path)
    page = PetSettingUI()
    page.profile_controls.profiles = PetProfiles({}, lambda: None)
    page.profile_controls.refresh()
    monkeypatch.setattr(page, '_target_geometry', lambda: None)
    page.builtin_character.setCurrentIndex(page.builtin_character.findData('inkside-pip'))
    page.use_builtin_character()
    assert not page.builtin_sprite_button.isEnabled()
    assert QThreadPool.globalInstance().waitForDone(120000)
    QCoreApplication.processEvents()
    return page


def _close(page):
    for pet in page.pet_list:
        pet.close()
    page.close()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_built_in_character_spawns_a_dressed_sprite_pet(tmp_path, monkeypatch):
    page = _ready_page(tmp_path, monkeypatch)
    try:
        assert page.builtin_sprite_button.isEnabled() and page.ready_to_play
        assert page.pet_image_path == str(tmp_path / 'pet-previews' / 'inkside-pip.png')
        assert page.puppet_script_path is None
        page.start_play_pet()
        pet = page.pet_list[-1]
        assert type(pet) is DesktopPetWidget
        assert pet.profile_session.state()['appearance']['character'] == REFERENCE
        assert pet._layered_playback.renderer is not None
        assert pet.asset_library.is_installed('inkside-pip', '1')
    finally:
        _close(page)


def test_a_pet_already_wearing_the_character_keeps_its_outfit(tmp_path, monkeypatch):
    from frontengine.show.pet.wardrobe import WardrobeDraft
    page = _ready_page(tmp_path, monkeypatch)
    try:
        page.start_play_pet()
        first = page.pet_list[-1]
        identity = first.profile_session.identifier
        catalog, _errors = first.asset_library.scan()
        draft = WardrobeDraft(page.profile_controls.profiles, identity, catalog)
        piece = next(asset for asset in catalog.assets('garment') if asset.identifier.startswith('inkside-pip-'))
        draft.equip({'id': piece.identifier, 'version': piece.version})
        draft.apply()
        dressed = page.profile_controls.profiles.get(identity)['appearance']
        first.close()
        page.profile_controls.selector.setCurrentIndex(page.profile_controls.selector.findData(identity))
        page.start_play_pet()
        assert page.profile_controls.profiles.get(identity)['appearance'] == dressed
    finally:
        _close(page)


def test_choosing_another_image_does_not_dress_the_pet(tmp_path, monkeypatch):
    from test_pet_profile_sessions import _sprite
    page = _ready_page(tmp_path, monkeypatch)
    try:
        page.pet_image_path = _sprite(tmp_path)
        page.start_play_pet()
        assert page.pet_list[-1].profile_session.state()['appearance']['character'] is None
    finally:
        _close(page)
