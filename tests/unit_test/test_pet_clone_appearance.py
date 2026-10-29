from pathlib import Path

from frontengine.show.pet.asset_library import PetAssetLibrary
from frontengine.show.pet.wardrobe import WardrobeDraft, asset_reference
from frontengine.ui.page.pet.pet_setting_ui import PetSettingUI
from frontengine.user_setting.pet_profiles import PetProfiles
from test_pet_profile_sessions import _sprite
from test_pet_variants import variant_asset


def test_clone_uses_source_sprite_and_custom_parts_after_page_selection_changes(tmp_path, monkeypatch):
    page = PetSettingUI()
    profiles = PetProfiles({}, lambda: None)
    page.profile_controls.profiles = profiles
    page.profile_controls.refresh()
    page.pet_image_path = _sprite(tmp_path)
    monkeypatch.setattr(page, '_target_geometry', lambda: None)
    page._spawn_pet()
    source = page.pet_list[0]
    try:
        library = PetAssetLibrary(tmp_path / 'custom-library')
        variant_asset(tmp_path / 'cat')
        asset = library.install(tmp_path / 'cat')
        source.asset_library = library
        catalog, _ = library.scan()
        draft = WardrobeDraft(profiles, source.profile_session.identifier, catalog)
        draft.choose_character(asset_reference(asset))
        draft.set_variant('eyes', 'sleepy')
        draft.save_outfit('Sleepy')
        draft.apply()
        before = source.profile_session.state()
        page.pet_image_path = str(tmp_path / 'unrelated.puppet')
        page.size_combobox.setCurrentText('256')
        source.clone_requested.emit()
        assert len(page.pet_list) == 2
        clone = page.pet_list[-1]
        assert clone.image_path == source.image_path
        assert clone.asset_library is source.asset_library
        assert clone._base_size == source._base_size
        assert clone.profile_session.identifier != source.profile_session.identifier
        assert clone.profile_session.state()['appearance'] == before['appearance']
        assert clone._current_pixmap().toImage() == source._current_pixmap().toImage()
        edited = WardrobeDraft(profiles, clone.profile_session.identifier, catalog)
        edited.set_variant('eyes', 'narrow')
        edited.apply()
        assert source.profile_session.state()['appearance'] == before['appearance']
        assert clone._current_pixmap().toImage() != source._current_pixmap().toImage()
        assert page.pet_image_path == str(tmp_path / 'unrelated.puppet')
    finally:
        for pet in page.pet_list:
            pet.close()
        page.close()


def test_puppet_clone_keeps_model_and_size_when_page_selects_sprite(tmp_path, monkeypatch):
    import pytest
    pytest.importorskip('Imervue.puppet.document_io')
    from test_puppet_startup_lifecycle import asset
    from frontengine.show.pet.puppet_pet import PuppetPetWidget
    page = PetSettingUI()
    page.profile_controls.profiles = PetProfiles({}, lambda: None)
    page.profile_controls.refresh()
    page.pet_image_path = str(asset(tmp_path))
    monkeypatch.setattr(page, '_target_geometry', lambda: None)
    page._spawn_pet()
    source = page.pet_list[0]
    try:
        page.pet_image_path = _sprite(tmp_path)
        page.size_combobox.setCurrentText('256')
        source.clone_requested.emit()
        clone = page.pet_list[-1]
        assert isinstance(clone, PuppetPetWidget)
        assert Path(clone.path) == Path(source.path)
        assert clone._initial_size == source._initial_size
        assert clone.profile_session.identifier != source.profile_session.identifier
        assert clone.script_path == source.script_path
    finally:
        for pet in page.pet_list:
            pet.close()
        page.close()
