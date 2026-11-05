"""Pet generation stays with the admitted data directory when its host changes cwd."""
import pytest

from frontengine.ui.page.pet.pet_setting_ui import PetSettingUI


@pytest.mark.parametrize('action', ['use_builtin_character', 'use_builtin_puppet'])
def test_generation_keeps_its_owners_directory(action, lifetime_factory, tmp_path, monkeypatch):
    lifetime = lifetime_factory()
    owner_directory = lifetime.storage.directory
    page = PetSettingUI(lifetime=lifetime)
    other = tmp_path / 'other-host-directory'
    other.mkdir()
    monkeypatch.chdir(other)
    jobs = []
    monkeypatch.setattr(lifetime, 'submit', jobs.append)
    try:
        getattr(page, action)()
        assert len(jobs) == 1
        job = jobs[0]
        if action == 'use_builtin_character':
            assert job.library.root == owner_directory / 'pet-assets'
            assert job.preview_folder == owner_directory / 'pet-previews'
        else:
            assert job.folder == owner_directory / 'pet-assets' / 'puppets'
    finally:
        page.close()


def test_saved_pet_wardrobe_keeps_its_owners_directory(lifetime_factory, tmp_path, monkeypatch):
    lifetime = lifetime_factory()
    owner_directory = lifetime.storage.directory
    page = PetSettingUI(lifetime=lifetime)
    identifier = page.profile_controls.profiles.create('Saved pet')['id']
    other = tmp_path / 'other-host-directory'
    other.mkdir()
    monkeypatch.chdir(other)
    try:
        page.profile_controls.wardrobe(identifier)
        dialog = page.profile_controls._wardrobes[identifier]
        assert dialog.library.root == owner_directory / 'pet-assets'
    finally:
        page.close()


def test_spawned_pet_reads_assets_from_its_owners_directory(lifetime_factory, tmp_path, monkeypatch):
    from PySide6.QtGui import QColor, QImage
    from frontengine.show.pet.asset_library import PetAssetLibrary
    lifetime = lifetime_factory()
    owner_directory = lifetime.storage.directory
    page = PetSettingUI(lifetime=lifetime)
    image = QImage(16, 16, QImage.Format.Format_ARGB32)
    image.fill(QColor('orange'))
    source = tmp_path / 'pet.png'
    assert image.save(str(source))
    page.pet_image_path = str(source)
    page.talk_checkbox.setChecked(False)
    page.sit_checkbox.setChecked(False)
    other = tmp_path / 'other-host-directory'
    other.mkdir()
    monkeypatch.chdir(other)
    try:
        page._spawn_profile_pet(None)
        assert len(page.pet_list) == 1
        assert page.pet_list[0].asset_library.root == owner_directory / 'pet-assets'
        pet = page.pet_list[0]
        custom_library = PetAssetLibrary(tmp_path / 'explicit-library')
        pet.asset_library = custom_library
        identifier = pet.profile_session.identifier
        page.profile_controls.wardrobe(identifier)
        assert page.profile_controls._wardrobes[identifier].library is custom_library
    finally:
        for pet in list(page.pet_list):
            pet.close()
        page.close()


def test_home_art_factory_keeps_its_owners_directory(lifetime_factory, tmp_path, monkeypatch):
    from frontengine.ui.page.pet_game.home_page import PetHomePage
    lifetime = lifetime_factory()
    owner_directory = lifetime.storage.directory
    page = PetHomePage(lifetime=lifetime)
    other = tmp_path / 'other-host-directory'
    other.mkdir()
    monkeypatch.chdir(other)
    try:
        assert page.art.library_factory().root == owner_directory / 'pet-assets'
    finally:
        assert page.shutdown()
        page.close()
