"""Wardrobe fit labelling, slot replacement, localized limits, try-on, comparison and safe switching."""
import json

import pytest

from frontengine.show.pet.asset_library import PetAssetLibrary
from frontengine.show.pet.wardrobe import AssetCatalog, WardrobeDraft, WardrobeError, garment_fit
from frontengine.ui.dialog.pet_wardrobe import PetWardrobeDialog
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.multi_language.retranslate import translate
from frontengine.utils.pet_pack.layered import load_layered_asset
from test_pet_layered import make_asset, write


def _garment(root, name, slots, *, template='chibi-cat', actions=None):
    data = make_asset(root / name, garment=True)
    data.update(slots=slots, template=template)
    data['actions'] = actions if actions is not None else {**data['actions'], 'greet': data['actions']['idle']}
    write(root / name, data)
    return load_layered_asset(root / name)


@pytest.fixture
def closet(tmp_path):
    make_asset(tmp_path / 'cat')
    data = json.loads((tmp_path / 'cat' / 'layered-pet.json').read_text(encoding='utf-8'))
    data['actions']['greet'] = data['actions']['idle']
    write(tmp_path / 'cat', data)
    cat = load_layered_asset(tmp_path / 'cat')
    idle_only = {'idle': data['actions']['idle']}
    assets = {
        'cat': cat,
        'hat': _garment(tmp_path, 'hat', ['head']),
        'hood': _garment(tmp_path, 'hood', ['head', 'body']),
        'coat': _garment(tmp_path, 'coat', ['body']),
        'dog_hat': _garment(tmp_path, 'dog_hat', ['head'], template='chibi-dog'),
        'stub': _garment(tmp_path, 'stub', ['head'], actions=idle_only),
    }
    profiles = PetProfiles({}, lambda: None)
    record = profiles.create('Closet')
    return profiles, record, AssetCatalog(tuple(assets.values())), assets


def _ref(asset):
    return {'id': asset.identifier, 'version': asset.version}


def test_fit_distinguishes_other_bodies_and_missing_animations(closet):
    _, _, _, assets = closet
    assert garment_fit(assets['cat'], assets['hat']) is None
    assert garment_fit(assets['cat'], assets['dog_hat']) == 'other_body'
    assert garment_fit(assets['cat'], assets['stub']) == 'missing_actions'
    assert garment_fit(None, assets['dog_hat']) is None


def test_equipping_replaces_what_shares_its_slots_and_cancel_restores(closet):
    profiles, record, catalog, assets = closet
    draft = WardrobeDraft(profiles, record['id'], catalog)
    draft.choose_character(_ref(assets['cat']))
    draft.equip(_ref(assets['hat']))
    draft.equip(_ref(assets['coat']))
    assert draft.equip(_ref(assets['hood'])) == ['hat', 'coat']
    assert draft.appearance['equipped']['head'] == draft.appearance['equipped']['body'] == _ref(assets['hood'])
    assert draft.equip(_ref(assets['hat'])) == ['hood']
    assert draft.appearance['equipped']['body'] is None
    draft.cancel()
    assert profiles.get(record['id']) == record


def test_outfit_limit_and_missing_character_are_localized(closet, monkeypatch):
    profiles, record, catalog, assets = closet
    draft = WardrobeDraft(profiles, record['id'], catalog)
    with pytest.raises(WardrobeError) as missing:
        draft.equip(_ref(assets['hat']))
    assert missing.value.localized(translate) == translate('pet_wardrobe_need_character')
    draft.choose_character(_ref(assets['cat']))
    for index in range(20):
        draft.save_outfit(f'Look {index}')
    with pytest.raises(WardrobeError) as limit:
        draft.save_outfit('One too many')
    assert '20' in limit.value.localized(translate)
    assert len(draft.appearance['saved_outfits']) == 20


class Library:
    def __init__(self, catalog):
        self.catalog = catalog

    def scan(self):
        return self.catalog, ()


def test_dialog_offers_only_fitting_pieces_and_explains_the_rest(closet):
    profiles, record, catalog, assets = closet
    dialog = PetWardrobeDialog(profiles, record['id'], library=Library(catalog))
    try:
        assert not dialog.slots['head'].isEnabled()
        assert dialog.status.text() == translate('pet_wardrobe_legacy')
        dialog.character.setCurrentIndex(dialog.character.findData(_ref(assets['cat'])))
        dialog._choose_character()
        head = dialog.slots['head']
        assert head.isEnabled()
        offered = [head.itemData(index) for index in range(head.count())]
        assert _ref(assets['dog_hat']) not in offered
        stub = head.findData(_ref(assets['stub']))
        assert stub >= 0 and not head.model().item(stub).isEnabled()
        assert translate('pet_wardrobe_incompatible') in head.itemText(stub)
    finally:
        dialog.close()


def test_try_on_replacement_note_and_comparison_preview(closet):
    profiles, record, catalog, assets = closet
    dialog = PetWardrobeDialog(profiles, record['id'], library=Library(catalog))
    try:
        dialog.character.setCurrentIndex(dialog.character.findData(_ref(assets['cat'])))
        dialog._choose_character()
        dialog.compare_button.setChecked(True)
        pinned = dialog._compare
        assert pinned is dialog.draft.preview and dialog.compare_preview.isVisibleTo(dialog)
        dialog.slots['head'].setCurrentIndex(dialog.slots['head'].findData(_ref(assets['hat'])))
        dialog._choose_slot('head')
        dialog.slots['body'].setCurrentIndex(dialog.slots['body'].findData(_ref(assets['hood'])))
        dialog._choose_slot('body')
        assert dialog.status.text() == translate('pet_wardrobe_replaced').format(items='hat')
        assert dialog._compare is pinned and dialog.draft.preview is not pinned
        dialog._render()
        assert dialog.compare_preview.pixmap() is not None
        dialog.compare_button.setChecked(False)
        assert dialog._compare is None and not dialog.compare_preview.isVisibleTo(dialog)
    finally:
        dialog.close()


def test_live_pet_switches_outfit_only_after_a_drag_ends(tmp_path, closet):
    from frontengine.show.pet.desktop_pet import DesktopPetWidget
    from test_pet_profile_sessions import _sprite
    profiles, record, catalog, assets = closet
    pet = DesktopPetWidget(_sprite(tmp_path), profiles=profiles, profile_id=record['id'], sit_on_windows=False)
    pet.show()
    try:
        first = WardrobeDraft(profiles, record['id'], catalog)
        first.choose_character(_ref(assets['cat']))
        first.apply()
        before = pet._layered_playback.renderer
        assert before is not None
        pet._dragging = True
        assert pet.profile_session.request('drag') == 'accepted'
        second = WardrobeDraft(profiles, record['id'], catalog)
        second.equip(_ref(assets['hat']))
        second.apply()
        assert pet._layered_playback.renderer is before
        pet._dragging = False
        pet.profile_session.request('cancel')
        assert pet._layered_playback.renderer is not before
    finally:
        pet.close()


def test_library_backed_dialog_still_scans_real_assets(tmp_path):
    make_asset(tmp_path / 'source')
    library = PetAssetLibrary(tmp_path / 'library')
    library.install(tmp_path / 'source')
    profiles = PetProfiles({}, lambda: None)
    dialog = PetWardrobeDialog(profiles, profiles.create()['id'], library=library)
    try:
        assert dialog.character.count() == 2
    finally:
        dialog.close()
