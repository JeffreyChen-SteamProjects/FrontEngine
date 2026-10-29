from frontengine.ui.dialog.pet_wardrobe import PetWardrobeDialog
import pytest
import test_pet_wardrobe as fixtures

wardrobe = fixtures.wardrobe


class CatalogLibrary:
    def __init__(self, catalog):
        self.catalog = catalog

    def scan(self):
        return self.catalog, ()


def test_dialog_stages_outfit_and_cancel_does_not_change_profile(wardrobe):
    profiles, first, _, draft, character, garment = wardrobe
    dialog = PetWardrobeDialog(profiles, first['id'], library=CatalogLibrary(draft.catalog))
    dialog.show()
    dialog.character.setCurrentIndex(dialog.character.findData(character))
    dialog._choose_character()
    dialog.slots['head'].setCurrentIndex(dialog.slots['head'].findData(garment))
    dialog._choose_slot('head')
    assert dialog.slots['neck'].currentData() == garment
    assert dialog.preview.pixmap() is not None
    assert profiles.get(first['id']) == first
    dialog.outfit_name.setText('Rain')
    dialog._save_outfit()
    assert dialog.outfits.count() == 1
    dialog.reject()
    assert profiles.get(first['id']) == first
    assert not dialog.timer.isActive()
    assert dialog.playback.renderer is None


def test_dialog_apply_then_cancel_keeps_last_applied_outfit(wardrobe):
    profiles, first, _, draft, character, garment = wardrobe
    dialog = PetWardrobeDialog(profiles, first['id'], library=CatalogLibrary(draft.catalog))
    try:
        dialog.character.setCurrentIndex(dialog.character.findData(character))
        dialog._choose_character()
        dialog.slots['head'].setCurrentIndex(dialog.slots['head'].findData(garment))
        dialog._choose_slot('head')
        assert dialog.apply_changes()
        saved = profiles.get(first['id'])
        dialog.slots['head'].setCurrentIndex(0)
        dialog._choose_slot('head')
        dialog.reject()
        assert profiles.get(first['id']) == saved
    finally:
        dialog.close()


def test_dialog_failed_save_keeps_preview_and_draft(wardrobe, monkeypatch):
    profiles, first, _, draft, character, _ = wardrobe
    dialog = PetWardrobeDialog(profiles, first['id'], library=CatalogLibrary(draft.catalog))
    try:
        dialog.character.setCurrentIndex(dialog.character.findData(character))
        dialog._choose_character()
        preview = dialog.playback.renderer

        def fail():
            raise OSError('disk unavailable')

        monkeypatch.setattr(profiles, 'save', fail)
        assert not dialog.apply_changes()
        assert dialog.playback.renderer is preview
        assert dialog.draft.appearance['character'] == character
        assert profiles.get(first['id']) == first
        assert 'disk unavailable' in dialog.status.text()
    finally:
        dialog.close()


def test_profile_controls_open_one_wardrobe_per_identity(wardrobe):
    from frontengine.ui.page.pet.pet_setting_ui import PetSettingUI

    profiles, first, _, _, _, _ = wardrobe
    page = PetSettingUI()
    try:
        page.profile_controls.profiles = profiles
        page.profile_controls.refresh(selected=first['id'])
        assert page.profile_controls.wardrobe_button.isEnabled()
        page.profile_controls.wardrobe_button.click()
        dialog = page.profile_controls._wardrobes[first['id']]
        assert dialog.isVisible()
        page.profile_controls.wardrobe_button.click()
        assert page.profile_controls._wardrobes[first['id']] is dialog
        dialog.reject()
        assert not dialog.timer.isActive()
    finally:
        page.close()


def test_background_install_refreshes_dialog_catalog(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog
    from PySide6.QtCore import QCoreApplication, QThreadPool
    from frontengine.show.pet.asset_library import PetAssetLibrary
    from frontengine.user_setting.pet_profiles import PetProfiles
    from test_pet_layered import make_asset

    source = tmp_path / 'cat'
    make_asset(source)
    profiles = PetProfiles({}, lambda: None)
    record = profiles.create()
    dialog = PetWardrobeDialog(profiles, record['id'], library=PetAssetLibrary(tmp_path / 'installed'))
    try:
        monkeypatch.setattr(QFileDialog, 'getExistingDirectory', lambda *_args: str(source))
        dialog._install()
        assert not dialog.install_button.isEnabled()
        assert QThreadPool.globalInstance().waitForDone(5000)
        QCoreApplication.processEvents()
        assert dialog._install_job is None
        assert dialog.install_button.isEnabled()
        assert dialog.character.count() == 2
        assert profiles.get(record['id']) == record
    finally:
        dialog.close()


@pytest.mark.parametrize('destroy', [False, True])
def test_close_during_install_cancels_staging_without_publishing(tmp_path, monkeypatch, destroy):
    from threading import Event
    from PySide6.QtWidgets import QFileDialog
    from PySide6.QtCore import QCoreApplication, QEvent, QThreadPool, Qt
    from shiboken6 import isValid
    from frontengine.show.pet.asset_library import PetAssetLibrary
    from frontengine.user_setting.pet_profiles import PetProfiles
    from test_pet_layered import make_asset

    ready, release = Event(), Event()

    class PausedLibrary(PetAssetLibrary):
        def _validate_images(self, asset):
            super()._validate_images(asset)
            ready.set()
            if not release.wait(5):
                raise TimeoutError('Test did not release installation')

    source = tmp_path / 'cat'
    make_asset(source)
    library = PausedLibrary(tmp_path / 'installed')
    profiles = PetProfiles({}, lambda: None)
    record = profiles.create()
    dialog = PetWardrobeDialog(profiles, record['id'], library=library)
    if not destroy:
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
    dialog.show()
    monkeypatch.setattr(QFileDialog, 'getExistingDirectory', lambda *_args: str(source))
    try:
        dialog._install()
        job = dialog._install_job
        assert ready.wait(5), 'Real worker did not reach validated staging'
        dialog.reject()
        assert job.cancel.is_set()
        assert not dialog.timer.isActive()
        assert dialog.playback.renderer is None
        if destroy:
            dialog.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        release.set()
        assert QThreadPool.globalInstance().waitForDone(5000)
        QCoreApplication.processEvents()
        assert list(library.root.iterdir()) == []
        assert profiles.get(record['id']) == record
        if not destroy:
            assert dialog._install_job is None
            assert not dialog.isVisible()
            assert dialog.playback.renderer is None
    finally:
        release.set()
        QThreadPool.globalInstance().waitForDone(5000)
        if isValid(dialog):
            dialog.close()


def test_failed_background_install_can_retry_same_version(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog
    from PySide6.QtCore import QCoreApplication, QThreadPool
    from frontengine.show.pet.asset_library import PetAssetLibrary
    from frontengine.user_setting.pet_profiles import PetProfiles
    from test_pet_layered import make_asset

    source = tmp_path / 'cat'
    make_asset(source)
    image = source / 'layer.png'
    original = image.read_bytes()
    image.write_bytes(b'corrupt PNG')
    library = PetAssetLibrary(tmp_path / 'installed')
    profiles = PetProfiles({}, lambda: None)
    record = profiles.create()
    dialog = PetWardrobeDialog(profiles, record['id'], library=library)
    monkeypatch.setattr(QFileDialog, 'getExistingDirectory', lambda *_args: str(source))
    try:
        dialog._install()
        assert QThreadPool.globalInstance().waitForDone(5000)
        QCoreApplication.processEvents()
        assert dialog.status.text()
        assert dialog.install_button.isEnabled()
        assert list(library.root.iterdir()) == []
        image.write_bytes(original)
        dialog._install()
        assert QThreadPool.globalInstance().waitForDone(5000)
        QCoreApplication.processEvents()
        assert dialog._install_job is None
        assert dialog.install_button.isEnabled()
        assert dialog.character.count() == 2
        assert len(list(library.root.iterdir())) == 1
        assert profiles.get(record['id']) == record
    finally:
        dialog.close()
