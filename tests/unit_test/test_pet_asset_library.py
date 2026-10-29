"""Installation and restart restoration use an independent local resource copy."""
import pytest
from PySide6.QtGui import QColor

from frontengine.show.pet.asset_library import PetAssetLibrary
from frontengine.show.pet.desktop_pet import DesktopPetWidget
from frontengine.show.pet.wardrobe import WardrobeDraft, asset_reference
from frontengine.user_setting.pet_profiles import PetProfiles
from test_pet_layered import make_asset


def test_install_relocates_only_declared_files_and_preserves_existing_version(tmp_path):
    source = tmp_path / 'cat'
    make_asset(source)
    (source / 'unrelated.txt').write_text('not a pet resource', encoding='utf-8')
    library = PetAssetLibrary(tmp_path / 'library')
    asset = library.install(source)
    assert asset.root != source
    assert (asset.root / 'layer.png').is_file()
    assert not (asset.root / 'unrelated.txt').exists()
    with pytest.raises(ValueError, match='already installed'):
        library.install(source)
    (source / 'layer.png').write_bytes(b'broken original')
    catalog, errors = library.scan()
    assert not errors
    assert catalog.resolve(asset_reference(asset), 'character').root == asset.root


def test_bad_install_leaves_no_partial_entry_and_scan_reports_corruption(tmp_path):
    source = tmp_path / 'cat'
    make_asset(source)
    library = PetAssetLibrary(tmp_path / 'library')
    original = (source / 'layer.png').read_bytes()
    (source / 'layer.png').write_bytes(b'invalid PNG')
    with pytest.raises(ValueError):
        library.install(source)
    assert list(library.root.iterdir()) == []
    (source / 'layer.png').write_bytes(original)
    installed = library.install(source)
    (installed.root / 'layered-pet.json').write_text('{', encoding='utf-8')
    catalog, errors = library.scan()
    assert not catalog.assets('character')
    assert len(errors) == 1


def test_cancelled_install_publishes_no_asset(tmp_path):
    from threading import Event

    source = tmp_path / 'cat'
    make_asset(source)
    library = PetAssetLibrary(tmp_path / 'library')
    cancel = Event()
    cancel.set()
    with pytest.raises(InterruptedError):
        library.install(source, cancel=cancel)
    assert list(library.root.iterdir()) == []


def test_saved_outfit_reopens_from_library_and_missing_asset_can_be_repaired(tmp_path):
    body, hat = tmp_path / 'cat', tmp_path / 'hat'
    make_asset(body)
    make_asset(hat, garment=True)
    library = PetAssetLibrary(tmp_path / 'library')
    character, garment = library.install(body), library.install(hat)
    catalog, _ = library.scan()
    profiles = PetProfiles({}, lambda: None)
    record = profiles.create()
    draft = WardrobeDraft(profiles, record['id'], catalog)
    draft.choose_character(asset_reference(character))
    draft.equip(asset_reference(garment))
    draft.apply()
    saved = profiles.get(record['id'])
    pet = DesktopPetWidget(str(body / 'layer.png'), profiles=profiles,
                           profile_id=record['id'], talk=False, asset_library=library)
    try:
        pet._set_active_sprite('idle')
        assert pet.appearance_error is None
        assert pet._current_pixmap().toImage().pixelColor(2, 2) == QColor('red')
    finally:
        pet.close()
    image = garment.root / 'layer.png'
    original = image.read_bytes()
    image.write_bytes(b'broken image')
    pet = DesktopPetWidget(str(body / 'layer.png'), profiles=profiles,
                           profile_id=record['id'], talk=False, asset_library=library)
    try:
        assert pet.appearance_error
        assert pet.profile_session.appearance_renderer is None
        assert profiles.get(record['id'])['appearance'] == saved['appearance']
        image.write_bytes(original)
        assert pet.restore_appearance()
        assert pet.appearance_error is None
        pet._set_active_sprite('idle')
        assert pet._current_pixmap().toImage().pixelColor(2, 2) == QColor('red')
    finally:
        pet.close()
