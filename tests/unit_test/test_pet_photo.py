from PySide6.QtGui import QColor, QImage

from frontengine.show.pet.desktop_pet import DesktopPetWidget
from frontengine.show.pet.layered_renderer import LayeredRenderer
from frontengine.ui.dialog.pet_photo import PetPhotoDialog, save_photo
from frontengine.user_setting.pet_profiles import PetProfiles
from test_pet_variants import variant_asset


def test_photo_png_preserves_alpha_parts_and_pose_without_changing_pet(tmp_path):
    asset = variant_asset(tmp_path / 'cat')
    profiles = PetProfiles({}, lambda: None)
    record = profiles.create()
    pet = DesktopPetWidget(str(asset.root / 'layer.png'), profiles=profiles,
                           profile_id=record['id'], talk=False, sit_on_windows=False)
    renderer = LayeredRenderer(asset, variants={'eyes': 'sleepy'})
    pet._layered_playback.set_renderer(renderer)
    pet.resize(16, 16)
    pet.motion.vx = -1
    try:
        pet.photo_action.trigger()
        dialog = pet._photo_dialog
        captured = dialog.image.copy()
        assert captured.pixelColor(13, 2) == QColor('red')
        assert captured.pixelColor(0, 0).alpha() == 0
        pet.motion.vx = 1
        assert dialog.image == captured
        dialog.pose.setCurrentIndex(dialog.pose.findData('sleep'))
        dialog.time.setValue(100)
        assert dialog.image.pixelColor(9, 2) == QColor('red')
        path = tmp_path / 'photo.png'
        assert dialog.save_to(path)
        saved = QImage(str(path))
        assert saved.pixelColor(9, 2) == QColor('red')
        assert saved.pixelColor(0, 0).alpha() == 0
        assert profiles.get(record['id']) == record
        assert pet._layered_playback.renderer is renderer
        dialog.close()
    finally:
        pet.close()


def test_photo_failure_retains_preview_and_retry_succeeds(tmp_path):
    image = QImage(2, 2, QImage.Format.Format_ARGB32)
    image.fill(QColor(255, 0, 0, 128))
    dialog = PetPhotoDialog(image)
    try:
        assert not dialog.time.isEnabled()
        assert not dialog.save_to(tmp_path / 'missing' / 'pet.png')
        assert dialog.image == image
        assert dialog.status.text()
        target = tmp_path / 'pet.png'
        target.write_bytes(b'previous')
        assert dialog.save_to(target)
        assert QImage(str(target)).pixelColor(0, 0) == QColor(255, 0, 0, 128)
    finally:
        dialog.close()


def test_null_photo_cannot_replace_existing_file(tmp_path):
    import pytest
    target = tmp_path / 'existing.png'
    target.write_bytes(b'original')
    with pytest.raises(ValueError):
        save_photo(QImage(), target)
    assert target.read_bytes() == b'original'
