from copy import deepcopy
import json

from PySide6.QtCore import QCoreApplication, QEvent

from frontengine.show.pet.asset_library import PetAssetLibrary
from frontengine.show.pet.wardrobe import asset_reference
from frontengine.ui.dialog.pet_wardrobe import PetWardrobeDialog
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import retranslator, translate
from test_pet_variants import variant_asset
from test_pet_layered import write


def test_language_switch_preserves_pending_wardrobe_and_preview(tmp_path):
    source = tmp_path / 'cat'
    variant_asset(source)
    data = json.loads((source / 'layered-pet.json').read_text(encoding='utf-8'))
    data['palette'] = {'fur': '#ff7417', 'eyes': '#fff1cf'}
    for action in data['actions'].values():
        for frame in action['frames']:
            for layer in frame['layers']:
                layer['tint'] = 'eyes' if layer['variant'][1] == 'sleepy' else 'fur'
    write(source, data)
    library = PetAssetLibrary(tmp_path / 'library')
    asset = library.install(source)
    profiles = PetProfiles({}, lambda: None)
    record = profiles.create()
    original_language = language_wrapper.language
    language_wrapper.reset_language('English')
    dialog = PetWardrobeDialog(profiles, record['id'], library=library)
    try:
        dialog.show()
        dialog.character.setCurrentIndex(dialog.character.findData(asset_reference(asset)))
        dialog._choose_character()
        dialog.variant_choice.setCurrentIndex(dialog.variant_choice.findData('sleepy'))
        dialog._choose_variant()
        dialog.color_region.setCurrentIndex(1)
        dialog._choose_swatch('#f45588')
        selected_region = dialog.color_region.currentData()
        dialog.outfit_name.setText('睡眼 · 雨衣')
        dialog._save_outfit()
        dialog.outfit_name.setText('尚未儲存的名稱')
        dialog.action.setCurrentText('sleep')
        dialog.mirror.setChecked(True)
        dialog.playback.pause()
        dialog.playback._elapsed = 0.137
        before = deepcopy(dialog.draft.appearance)
        frame = dialog.playback.frame()
        selected_outfit = dialog.outfits.currentData()
        for language in list(language_wrapper.choose_language_dict) * 3:
            language_wrapper.reset_language(language)
            retranslator.apply()
            assert dialog.character.itemText(0) == translate('pet_wardrobe_none')
            assert all(control.itemText(0) == translate('pet_wardrobe_none')
                       for control in dialog.slots.values())
            assert dialog.variant_choice.itemText(0) == translate('pet_custom_reset')
            assert dialog.draft.appearance == before
            assert profiles.get(record['id']) == record
            assert dialog.variant_choice.currentData() == 'sleepy'
            assert dialog.color_region.currentData() == selected_region
            assert dialog.outfits.currentData() == selected_outfit
            assert dialog.outfit_name.text() == '尚未儲存的名稱'
            assert dialog.action.currentText() == 'sleep'
            assert dialog.mirror.isChecked()
            assert dialog.playback.frame() == frame
        assert dialog.apply_changes()
        assert profiles.get(record['id'])['appearance'] == before
    finally:
        dialog.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        language_wrapper.reset_language(original_language)
        retranslator.apply()


def test_missing_asset_label_retranslates_without_changing_saved_reference(tmp_path):
    profiles = PetProfiles({}, lambda: None)
    record = profiles.create()
    appearance = deepcopy(record['appearance'])
    appearance['character'] = {'id': 'absent-cat', 'version': '1'}
    profiles.update(record['id'], {'appearance': appearance})
    original_language = language_wrapper.language
    language_wrapper.reset_language('English')
    dialog = PetWardrobeDialog(profiles, record['id'], library=PetAssetLibrary(tmp_path / 'empty'))
    try:
        language_wrapper.reset_language('Traditional_Chinese')
        retranslator.apply()
        assert dialog.character.currentText() == translate('pet_wardrobe_missing') + ': absent-cat'
        assert dialog.character.currentData() == appearance['character']
        assert profiles.get(record['id'])['appearance'] == appearance
    finally:
        dialog.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        language_wrapper.reset_language(original_language)
        retranslator.apply()
