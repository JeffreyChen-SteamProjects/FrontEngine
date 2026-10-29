import copy

import pytest
from PySide6.QtGui import QColor, QImage

from frontengine.show.pet.asset_library import PetAssetLibrary
from frontengine.show.pet.layered_renderer import LayeredRenderer
from frontengine.show.pet.wardrobe import AssetCatalog, WardrobeDraft, asset_reference
from frontengine.ui.dialog.pet_wardrobe import PetWardrobeDialog
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.pet_pack.layered import load_layered_asset
from test_pet_layered import make_asset, write


def variant_asset(root):
    data = make_asset(root)
    data['variants'] = {'eyes': {'name': 'Eyes', 'default': 'narrow',
                                'choices': {'narrow': 'Narrow', 'sleepy': 'Sleepy'}}}
    image = QImage(2, 2, QImage.Format.Format_ARGB32)
    image.fill(QColor('red'))
    assert image.save(str(root / 'sleepy.png'))
    for frame in data['actions']['idle']['frames']:
        frame['layers'][0]['variant'] = ['eyes', 'narrow']
        alternative = copy.deepcopy(frame['layers'][0])
        alternative.update(image='sleepy.png', variant=['eyes', 'sleepy'])
        frame['layers'].append(alternative)
    data['actions']['sleep'] = copy.deepcopy(data['actions']['idle'])
    write(root, data)
    return load_layered_asset(root)


def test_selected_parts_follow_animation_and_mirroring(tmp_path):
    asset = variant_asset(tmp_path / 'cat')
    default = LayeredRenderer(asset)
    selected = LayeredRenderer(asset, variants={'eyes': 'sleepy'})
    assert default.render('idle', 0).pixelColor(2, 2) == QColor('blue')
    for action in ('idle', 'sleep'):
        assert selected.render(action, 100).pixelColor(6, 2) == QColor('red')
        assert selected.render(action, 100).pixelColor(2, 2).alpha() == 0
        assert selected.render(action, 100, mirrored=True).pixelColor(9, 2) == QColor('red')


def test_parts_outfits_cross_character_and_portable_restore(tmp_path):
    asset = variant_asset(tmp_path / 'cat')
    make_asset(tmp_path / 'other')
    other = load_layered_asset(tmp_path / 'other')
    profiles = PetProfiles({}, lambda: None)
    first, second = profiles.create(), profiles.create()
    catalog = AssetCatalog((asset, other))
    draft = WardrobeDraft(profiles, first['id'], catalog)
    draft.choose_character(asset_reference(asset))
    draft.set_variant('eyes', 'sleepy')
    outfit = draft.save_outfit('Sleepy cat')
    draft.choose_character(asset_reference(other))
    assert 'variants' not in draft.appearance
    draft.wear_outfit(outfit)
    assert draft.preview.render('sleep', 0).pixelColor(2, 2) == QColor('red')
    draft.apply()
    assert profiles.get(second['id']) == second
    profiles.export_profile(first['id'], tmp_path / 'pet.json')
    imported = profiles.import_profile(tmp_path / 'pet.json')
    restored = WardrobeDraft(profiles, imported['id'], catalog)
    assert restored.prepare_preview().render('idle', 0).pixelColor(2, 2) == QColor('red')
    restored.set_variant('eyes', None)
    assert restored.preview.render('idle', 0).pixelColor(2, 2) == QColor('blue')
    restored.cancel()
    assert restored.appearance['variants'] == {'eyes': 'sleepy'}


@pytest.mark.parametrize('corruption', ['missing_frame', 'unknown', 'bad_default', 'garment'])
def test_incomplete_or_invalid_manifest_rejected(tmp_path, corruption):
    import json
    root = tmp_path / 'cat'
    variant_asset(root)
    data = json.loads((root / 'layered-pet.json').read_text())
    if corruption == 'missing_frame':
        data['actions']['sleep']['frames'][1]['layers'].pop()
    elif corruption == 'unknown':
        data['actions']['idle']['frames'][0]['layers'][0]['variant'][1] = 'missing'
    elif corruption == 'bad_default':
        data['variants']['eyes']['default'] = 'missing'
    else:
        data.update(kind='garment', slots=['head'])
    write(root, data)
    with pytest.raises(ValueError):
        load_layered_asset(root)


def test_invalid_draft_keeps_last_preview_and_saved_state(tmp_path):
    asset = variant_asset(tmp_path / 'cat')
    profiles = PetProfiles({}, lambda: None)
    record = profiles.create()
    draft = WardrobeDraft(profiles, record['id'], AssetCatalog((asset,)))
    draft.choose_character(asset_reference(asset))
    before = draft.appearance
    for group, choice in [('missing', 'narrow'), ('eyes', 'missing'), ('eyes', True)]:
        with pytest.raises(ValueError):
            draft.set_variant(group, choice)
        assert draft.appearance == before
    assert profiles.get(record['id']) == record


def test_installed_parts_dialog_preview_apply_and_cancel(tmp_path):
    source = tmp_path / 'cat'
    variant_asset(source)
    library = PetAssetLibrary(tmp_path / 'library')
    asset = library.install(source)
    profiles = PetProfiles({}, lambda: None)
    record = profiles.create()
    dialog = PetWardrobeDialog(profiles, record['id'], library=library)
    try:
        assert not dialog.variant_choice.isEnabled()
        dialog.character.setCurrentIndex(dialog.character.findData(asset_reference(asset)))
        dialog._choose_character()
        dialog.variant_choice.setCurrentIndex(dialog.variant_choice.findData('sleepy'))
        dialog._choose_variant()
        assert dialog.draft.preview.render('idle', 0).pixelColor(2, 2) == QColor('red')
        assert profiles.get(record['id']) == record
        assert dialog.apply_changes()
        saved = profiles.get(record['id'])
        dialog.variant_choice.setCurrentIndex(0)
        dialog._choose_variant()
        dialog.reject()
        assert profiles.get(record['id']) == saved
        assert saved['appearance']['variants'] == {'eyes': 'sleepy'}
    finally:
        dialog.close()


def test_live_parts_publish_only_after_save_and_restore_on_reopen(tmp_path, monkeypatch):
    from frontengine.show.pet.desktop_pet import DesktopPetWidget

    source = tmp_path / 'cat'
    variant_asset(source)
    library = PetAssetLibrary(tmp_path / 'library')
    asset = library.install(source)
    profiles = PetProfiles({}, lambda: None)
    record = profiles.create()
    catalog, _ = library.scan()
    draft = WardrobeDraft(profiles, record['id'], catalog)
    pet = DesktopPetWidget(str(source / 'layer.png'), profiles=profiles,
                           profile_id=record['id'], talk=False, sit_on_windows=False,
                           asset_library=library)
    try:
        draft.choose_character(asset_reference(asset))
        draft.apply()
        draft.set_variant('eyes', 'sleepy')
        def fail():
            raise OSError('disk unavailable')
        with monkeypatch.context() as patch:
            patch.setattr(profiles, 'save', fail)
            with pytest.raises(OSError):
                draft.apply()
        assert pet._current_pixmap().toImage().pixelColor(2, 2) == QColor('blue')
        draft.apply()
        assert pet._current_pixmap().toImage().pixelColor(2, 2) == QColor('red')
    finally:
        pet.close()
    reopened = DesktopPetWidget(str(source / 'layer.png'), profiles=profiles,
                                profile_id=record['id'], talk=False, sit_on_windows=False,
                                asset_library=library)
    try:
        assert reopened._current_pixmap().toImage().pixelColor(2, 2) == QColor('red')
    finally:
        reopened.close()
