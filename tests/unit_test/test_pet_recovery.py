from PySide6.QtCore import QCoreApplication, QEvent, QRect, Qt
import pytest

from frontengine.show.pet.recovery import recover_pet
from frontengine.show.pet.focus_companions import FocusCompanions
import test_pet_social_modes as fixtures

social_pets = fixtures.social_pets


def test_recovery_page_moves_only_selected_pet_and_clears_flight(social_pets, monkeypatch):
    page, pets = social_pets
    pet, other = pets[:2]
    pet.set_pet_window_flag()
    pet.show()
    controls = page.profile_controls
    controls.profiles = pet.profile_session.profiles
    controls.refresh(selected=pet.profile_session.identifier)
    screen = pet.screen()
    area = QRect(-1000, -500, 800, 600)
    monkeypatch.setattr(screen, 'availableGeometry', lambda: area)
    monkeypatch.setattr(page, '_target_geometry', lambda: (area, screen))
    pet.place_for_focus(5000, 5000)
    pet.motion.throw(40, -30)
    other_position = other.pos()
    before = pet.profile_session.state()
    controls.recover_button.click()
    assert area.contains(pet.geometry())
    assert (pet.motion.x, pet.motion.y) == (pet.x(), pet.y())
    assert pet.motion.bounds == (-1000, -500, -200, 100)
    assert not pet.motion._airborne
    assert not pet.motion.on_platform
    assert pet.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    assert other.pos() == other_position
    assert pet.profile_session.state() == before


def test_recover_hidden_pet_and_focus_stop_does_not_restore_old_position(social_pets):
    _, pets = social_pets
    pet = pets[0]
    focus = FocusCompanions()
    focus.begin([pet])
    pet.hide()
    recover_pet(pet, pet.screen())
    restored = pet.pos()
    assert pet.isVisible()
    focus.stop()
    assert pet.pos() == restored
    assert pet.companion.mode == 'play'


def test_recovery_removes_toy_and_cancels_unfinished_care(social_pets):
    _, pets = social_pets
    pet = pets[0]
    pet.start_ball()
    toy = pet._toy
    recover_pet(pet, pet.screen())
    assert pet._toy is None
    assert not toy.isVisible()
    pet.profile_session.request('groom')
    recover_pet(pet, pet.screen())
    pet.profile_session.advance(4)
    assert pet.companion.action is None
    assert pet.companion.growth.affection == 0


def test_recovery_rejects_oversized_pet_without_mutation(social_pets, monkeypatch):
    _, pets = social_pets
    pet = pets[0]
    before = pet.pos()
    screen = pet.screen()
    monkeypatch.setattr(screen, 'availableGeometry', lambda: QRect(0, 0, 10, 10))
    with pytest.raises(ValueError, match='larger'):
        recover_pet(pet, screen)
    assert pet.pos() == before


def test_inactive_recovery_reports_status_without_spawning(social_pets):
    page, pets = social_pets
    controls = page.profile_controls
    controls.profiles = pets[0].profile_session.profiles
    record = controls.profiles.create('Inactive')
    controls.refresh(selected=record['id'])
    controls.recover_button.click()
    assert controls.status.text()
    assert len(page.pet_list) == 3


def test_puppet_recovery_keeps_identity_and_model(tmp_path):
    pytest.importorskip('Imervue.puppet.document_io')
    from frontengine.show.pet.puppet_pet import PuppetPetWidget
    from frontengine.user_setting.pet_profiles import PetProfiles
    from test_puppet_startup_lifecycle import asset

    pet = PuppetPetWidget(asset(tmp_path), size=(128, 192), profiles=PetProfiles({}, lambda: None))
    before = pet.profile_session.state()
    document = pet.canvas.document()
    try:
        pet.move(10000, 10000)
        recover_pet(pet, pet.screen())
        assert pet.isVisible()
        assert pet.screen().availableGeometry().contains(pet.geometry())
        assert pet.canvas.document() is document
        assert pet.profile_session.state() == before
    finally:
        pet.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
