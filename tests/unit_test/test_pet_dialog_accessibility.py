import pytest
from PySide6.QtGui import QAccessible, QImage
from PySide6.QtWidgets import QFormLayout

from frontengine.show.pet.asset_library import PetAssetLibrary
from frontengine.ui.dialog.pet_photo import PetPhotoDialog
from frontengine.ui.dialog.pet_wardrobe import PetWardrobeDialog
from frontengine.user_setting.pet_profiles import PetProfiles


@pytest.mark.parametrize('field', ['character', 'head', 'neck', 'body', 'back',
                                  'action', 'color_region', 'variant_group',
                                  'variant_choice', 'outfits', 'outfit_name'])
def test_wardrobe_field_accessible_name_tracks_visible_label(field, tmp_path, lifetime_factory):
    lifetime = lifetime_factory()
    profiles = PetProfiles({}, lambda: None)
    record = profiles.create()
    dialog = PetWardrobeDialog(profiles, record['id'], library=PetAssetLibrary(tmp_path / 'assets'),
                               lifetime=lifetime)
    try:
        control = dialog.slots[field] if field in dialog.slots else getattr(dialog, field)
        label = dialog.findChild(QFormLayout).labelForField(control)
        accessible = QAccessible.queryAccessibleInterface(control)
        assert accessible.text(QAccessible.Text.Name) == label.text()
        label.setText('Updated ' + label.text())
        assert accessible.text(QAccessible.Text.Name) == label.text()
        assert profiles.get(record['id']) == record
    finally:
        dialog.close()


@pytest.mark.parametrize('field', ['pose', 'time'])
def test_photo_field_accessible_name_tracks_visible_label(field):
    image = QImage(2, 2, QImage.Format.Format_ARGB32)
    image.fill(0)
    dialog = PetPhotoDialog(image)
    try:
        control = getattr(dialog, field)
        label = dialog.findChild(QFormLayout).labelForField(control)
        accessible = QAccessible.queryAccessibleInterface(control)
        assert accessible.text(QAccessible.Text.Name) == label.text()
        label.setText('Updated ' + label.text())
        assert accessible.text(QAccessible.Text.Name) == label.text()
        assert dialog.image == image
    finally:
        dialog.close()
