import pytest
from PySide6.QtGui import QColor, QImage

from frontengine.show.pet.desktop_pet import DesktopPetWidget
from frontengine.show.pet.layered_renderer import LayeredRenderer
from frontengine.ui.dialog.pet_photo import PetPhotoDialog, save_photo
from frontengine.user_setting.pet_profiles import PetProfiles
from test_pet_variants import variant_asset


def test_cancelled_photo_destination_allows_later_save(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog

    image = QImage(2, 2, QImage.Format.Format_ARGB32)
    image.fill(QColor(255, 0, 0, 128))
    dialog = PetPhotoDialog(image)
    target = tmp_path / 'photo.png'
    choices = iter([('', ''), (str(target), 'PNG (*.png)')])
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *_args: next(choices))
    try:
        dialog.choose_destination()
        assert not target.exists()
        dialog.choose_destination()
        assert QImage(str(target)) == image
    finally:
        dialog.close()


@pytest.mark.parametrize('closing', ['reject', 'close', 'destroy'])
@pytest.mark.parametrize('existing', [False, True])
def test_photo_closed_during_destination_choice_never_writes(tmp_path, monkeypatch, closing, existing):
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QFileDialog
    from shiboken6 import isValid

    image = QImage(2, 2, QImage.Format.Format_ARGB32)
    image.fill(QColor('red'))
    dialog = PetPhotoDialog(image)
    dialog.show()
    target = tmp_path / 'photo.png'
    if existing:
        target.write_bytes(b'original')

    def choose(*_args):
        if closing == 'reject':
            dialog.reject()
        else:
            dialog.close()
        if closing == 'destroy':
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        return str(target), 'PNG (*.png)'

    monkeypatch.setattr(QFileDialog, 'getSaveFileName', choose)
    try:
        dialog.choose_destination()
        monkeypatch.setattr(QFileDialog, 'getSaveFileName',
                            lambda *_args: pytest.fail('Closed photo opened another file picker'))
        dialog.choose_destination()
        assert not dialog.save_to(target)
        if existing:
            assert target.read_bytes() == b'original'
        else:
            assert not target.exists()
    finally:
        if isValid(dialog):
            dialog.close()


@pytest.mark.parametrize('pose', [None, 'sleep'])
def test_photo_language_change_preserves_pose_time_and_image(tmp_path, pose):
    from frontengine.utils.multi_language.language_wrapper import language_wrapper
    from frontengine.utils.multi_language.retranslate import retranslator, translate

    previous = language_wrapper.language
    renderer = LayeredRenderer(variant_asset(tmp_path / 'cat'))
    image = QImage(2, 2, QImage.Format.Format_ARGB32)
    image.fill(QColor('red'))
    dialog = PetPhotoDialog(image, renderer)
    try:
        dialog.pose.setCurrentIndex(dialog.pose.findData(pose))
        dialog.time.setValue(100)
        selected_time = dialog.time.value()
        selected_image = dialog.image.copy()
        choices = [dialog.pose.itemData(index) for index in range(dialog.pose.count())]
        for language in language_wrapper.choose_language_dict:
            assert language_wrapper.reset_language(language)
            retranslator.apply()
            assert dialog.pose.itemText(0) == translate('pet_photo_current')
            assert dialog.pose.currentData() == pose
            assert dialog.time.value() == selected_time
            assert dialog.image == selected_image
            assert [dialog.pose.itemData(index) for index in range(dialog.pose.count())] == choices
    finally:
        language_wrapper.reset_language(previous)
        retranslator.apply()
        dialog.close()


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
    target = tmp_path / 'existing.png'
    target.write_bytes(b'original')
    with pytest.raises(ValueError):
        save_photo(QImage(), target)
    assert target.read_bytes() == b'original'
