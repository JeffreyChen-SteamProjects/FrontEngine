import test_pet_social_modes as fixtures
import test_puppet_petting as puppet_fixtures

social_pets = fixtures.social_pets
puppet = puppet_fixtures.puppet


def choose(controls, action, kind=None):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    index = controls.interaction.findData(action + ':' + kind if kind else action)
    assert index >= 0
    controls.interaction.setCurrentIndex(index)
    QTest.keyClick(controls.interact_button, Qt.Key.Key_Space)


def test_manager_commands_target_selected_live_identity(social_pets):
    page, pets = social_pets
    first, second = pets[:2]
    controls = page.profile_controls
    controls.profiles = first.profile_session.profiles
    controls.refresh(selected=first.profile_session.identifier)
    choose(controls, 'pet')
    assert first.companion.action == 'pet'
    assert first._petting is None
    assert second.companion.action is None
    first.profile_session.advance(2)
    assert first.companion.growth.affection == 2
    controls.selector.setCurrentIndex(controls.selector.findData(second.profile_session.identifier))
    choose(controls, 'work')
    assert second.companion.mode == 'work'
    assert first.companion.mode == 'play'
    choose(controls, 'feed', 'music')
    assert second.companion.action == 'feed'
    choose(controls, 'cancel')
    second.profile_session.advance(2)
    assert second.companion.growth.affection == 0


def test_manager_unavailable_pet_does_not_spawn_or_mutate(social_pets):
    page, pets = social_pets
    controls = page.profile_controls
    controls.profiles = pets[0].profile_session.profiles
    controls.refresh(selected=None)
    controls.selector.setCurrentIndex(0)
    assert not controls.interact_button.isEnabled()
    record = controls.profiles.create('Inactive')
    controls.refresh(selected=record['id'])
    choose(controls, 'feed', 'feast')
    assert controls.status.text()
    assert controls.profiles.get(record['id']) == record
    assert len(page.pet_list) == 3
    pet = pets[0]
    controls.refresh(selected=pet.profile_session.identifier)
    pet.hide()
    before = pet.profile_session.state()
    choose(controls, 'pet')
    assert pet.profile_session.state() == before
    assert not pet.isVisible()
    pet.close()
    choose(controls, 'groom')
    assert controls.status.text()


def test_manager_clears_pointer_interaction_and_keeps_cooldown(social_pets):
    page, pets = social_pets
    pet = pets[0]
    controls = page.profile_controls
    controls.profiles = pet.profile_session.profiles
    controls.refresh(selected=pet.profile_session.identifier)
    pet.start_ball()
    choose(controls, 'groom')
    assert pet._toy is None
    pet.profile_session.advance(3)
    before = pet.companion.growth.affection
    choose(controls, 'groom')
    assert pet.companion.action is None
    assert pet.companion.growth.affection == before
    selected = controls.interaction.currentData()
    controls.refresh()
    assert controls.interaction.currentData() == selected


def test_manager_puppet_care_uses_same_completion(puppet):
    from frontengine.ui.page.pet.pet_setting_ui import PetSettingUI
    page = PetSettingUI()
    try:
        controls = page.profile_controls
        controls.profiles = puppet.profile_session.profiles
        controls.refresh(selected=puppet.profile_session.identifier)
        choose(controls, 'pet')
        assert puppet.profile_session.companion.action == 'pet'
        assert puppet._petting is None
        puppet.profile_session.advance(2)
        assert puppet.profile_session.companion.growth.affection == 2
        choose(controls, 'rest')
        assert puppet.profile_session.companion.mode == 'rest'
    finally:
        page.close()
