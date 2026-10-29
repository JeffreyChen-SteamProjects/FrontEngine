import copy

import pytest
from PySide6.QtGui import QColor, QImage

from frontengine.show.pet.layered_renderer import LayeredRenderer
from frontengine.show.pet.wardrobe import AssetCatalog, WardrobeDraft, asset_reference
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.pet_pack.layered import load_layered_asset
from test_pet_layered import make_asset, write


def palette_asset(root):
    data = make_asset(root)
    data['palette'] = {'fur': '#ff8800'}
    mask = QImage(2, 2, QImage.Format.Format_ARGB32)
    mask.fill(QColor(255, 255, 255, 128))
    assert mask.save(str(root / 'layer.png'))
    outline = QImage(1, 1, QImage.Format.Format_ARGB32)
    outline.fill(QColor('black'))
    assert outline.save(str(root / 'outline.png'))
    for frame in data['actions']['idle']['frames']:
        frame['layers'][0]['tint'] = 'fur'
        frame['layers'].append({'image': 'outline.png', 'z': 1, 'anchor': 'head', 'offset': [2, 0]})
    write(root, data)
    return load_layered_asset(root)


def test_mask_tint_preserves_alpha_and_uncolored_details(tmp_path):
    asset = palette_asset(tmp_path / 'cat')
    default = LayeredRenderer(asset)
    custom = LayeredRenderer(asset, colors={'cat@1': {'fur': '#00ff00'}})
    original = default.render('idle', 0)
    image = custom.render('idle', 0)
    assert original.pixelColor(2, 2).red() == 255
    assert image.pixelColor(2, 2) == QColor(0, 255, 0, 128)
    assert image.pixelColor(4, 2) == QColor('black')
    assert image.pixelColor(0, 0).alpha() == 0
    assert default.render('idle', 0) == original


def test_palette_draft_saved_outfit_export_and_reset_remain_independent(tmp_path):
    asset = palette_asset(tmp_path / 'cat')
    profiles = PetProfiles({}, lambda: None)
    first, second = profiles.create(), profiles.create()
    catalog = AssetCatalog((asset,))
    draft = WardrobeDraft(profiles, first['id'], catalog)
    reference = asset_reference(asset)
    draft.choose_character(reference)
    draft.set_color(reference, 'fur', '#00ff00')
    identifier = draft.save_outfit('Green')
    draft.set_color(reference, 'fur', '#0000ff')
    assert draft.appearance['saved_outfits'][0]['colors']['cat@1']['fur'] == '#00ff00'
    draft.wear_outfit(identifier)
    draft.apply()
    assert profiles.get(second['id']) == second
    destination = tmp_path / 'save.json'
    profiles.export_profile(first['id'], destination)
    imported = profiles.import_profile(destination)
    reopened = WardrobeDraft(profiles, imported['id'], catalog)
    assert reopened.prepare_preview().render('idle', 0).pixelColor(2, 2) == QColor(0, 255, 0, 128)
    reopened.set_color(reference, 'fur', None)
    assert reopened.preview.render('idle', 0).pixelColor(2, 2).red() == 255
    reopened.cancel()
    assert reopened.appearance['colors']['cat@1']['fur'] == '#00ff00'


@pytest.mark.parametrize('colors', [
    {'cat@1': {'fur': 'red'}}, {'cat@1': {'fur': '#12345678'}},
    {'cat@1': {'fur': True}}, {'../cat@1': {'fur': '#ffffff'}},
    {'cat@1': {str(index): '#ffffff' for index in range(9)}},
])
def test_invalid_saved_colors_rejected_without_mutation(colors):
    profiles = PetProfiles({}, lambda: None)
    record = profiles.create()
    appearance = copy.deepcopy(record['appearance'])
    appearance['colors'] = colors
    with pytest.raises(ValueError):
        profiles.update(record['id'], {'appearance': appearance})
    assert profiles.get(record['id']) == record


def test_undeclared_region_and_unequipped_asset_rejected(tmp_path):
    asset = palette_asset(tmp_path / 'cat')
    for colors in ({'cat@1': {'eyes': '#ffffff'}}, {'other@1': {'fur': '#ffffff'}}):
        with pytest.raises(ValueError):
            LayeredRenderer(asset, colors=colors)
    data = make_asset(tmp_path / 'invalid')
    data['actions']['idle']['frames'][0]['layers'][0]['tint'] = 'undeclared'
    write(tmp_path / 'invalid', data)
    with pytest.raises(ValueError, match='undeclared'):
        load_layered_asset(tmp_path / 'invalid')


def test_dialog_color_preview_apply_and_restore(tmp_path, monkeypatch):
    from frontengine.show.pet.asset_library import PetAssetLibrary
    from frontengine.ui.dialog.pet_wardrobe import PetWardrobeDialog
    from PySide6.QtWidgets import QColorDialog

    source = tmp_path / 'cat'
    palette_asset(source)
    library = PetAssetLibrary(tmp_path / 'library')
    asset = library.install(source)
    profiles = PetProfiles({}, lambda: None)
    record = profiles.create()
    dialog = PetWardrobeDialog(profiles, record['id'], library=library)
    try:
        assert not dialog.color_button.isEnabled()
        dialog.character.setCurrentIndex(dialog.character.findData(asset_reference(asset)))
        dialog._choose_character()
        assert dialog.color_button.isEnabled()
        monkeypatch.setattr(QColorDialog, 'getColor', lambda *_args: QColor('#00ff00'))
        dialog._choose_color()
        assert dialog.draft.preview.render('idle', 0).pixelColor(2, 2) == QColor(0, 255, 0, 128)
        assert profiles.get(record['id']) == record
        assert dialog.apply_changes()
        saved = profiles.get(record['id'])
        assert saved['appearance']['colors']['cat@1']['fur'] == '#00ff00'
        dialog._reset_color()
        assert dialog.draft.preview.render('idle', 0).pixelColor(2, 2).red() == 255
        dialog.reject()
        assert profiles.get(record['id']) == saved
    finally:
        dialog.close()


def test_style_swatches_preview_without_committing_and_reopen_after_apply(tmp_path):
    from frontengine.show.pet.asset_library import PetAssetLibrary
    from frontengine.ui.dialog.pet_wardrobe import PetWardrobeDialog

    palette_asset(tmp_path / 'cat')
    library = PetAssetLibrary(tmp_path / 'library')
    asset = library.install(tmp_path / 'cat')
    profiles = PetProfiles({}, lambda: None)
    record, other = profiles.create(), profiles.create()
    dialog = PetWardrobeDialog(profiles, record['id'], library=library)
    try:
        assert all(not button.isEnabled() for button in dialog.swatches.values())
        dialog.character.setCurrentIndex(dialog.character.findData(asset_reference(asset)))
        dialog._choose_character()
        for value, button in dialog.swatches.items():
            assert button.isEnabled()
            assert button.accessibleName() == value
            button.click()
            image = dialog.draft.preview.render('idle', 0)
            expected = QColor(value)
            expected.setAlpha(128)
            actual = image.pixelColor(2, 2)
            assert actual.alpha() == 128
            assert all(abs(a - b) <= 1 for a, b in zip(actual.getRgb(), expected.getRgb()))
            assert image.pixelColor(4, 2) == QColor('black')
            assert profiles.get(record['id']) == record
        assert dialog.apply_changes()
        saved = profiles.get(record['id'])
        assert saved['appearance']['colors']['cat@1']['fur'] == '#f45588'
        dialog.swatches['#171613'].click()
        dialog.reject()
        assert profiles.get(record['id']) == saved
        assert profiles.get(other['id']) == other
    finally:
        dialog.close()
    reopened = PetWardrobeDialog(profiles, record['id'], library=library)
    try:
        assert reopened.draft.appearance['colors']['cat@1']['fur'] == '#f45588'
        reopened.color_reset.click()
        assert reopened.draft.appearance.get('colors', {}) == {}
    finally:
        reopened.close()
