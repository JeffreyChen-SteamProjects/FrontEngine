import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

import test_pet_social_modes as fixtures
import test_puppet_petting as puppet_fixtures

social_pets = fixtures.social_pets
puppet = puppet_fixtures.puppet


def call_controls(page, pet):
    controls = page.profile_controls
    controls.profiles = pet.profile_session.profiles
    controls.refresh(selected=pet.profile_session.identifier)
    QTest.keyClick(controls.interaction, Qt.Key.Key_End)
    assert controls.interaction.currentData() == 'call'
    assert controls.call_x.isEnabled() and controls.call_y.isEnabled()
    for control, value in ((controls.call_x, '-80'), (controls.call_y, '-40')):
        QTest.keyClick(control, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        QTest.keyClicks(control, value)
        control.interpretText()
        assert control.value() == int(value)
    return controls


@pytest.mark.parametrize('behaviour', ['floor', 'wander', 'chase'])
@pytest.mark.parametrize('activity', ['call', 'light'])
def test_keyboard_call_places_selected_pet_target_and_arrives(social_pets, behaviour, activity):
    page, pets = social_pets
    pet, other = pets[:2]
    pet.motion.behaviour = behaviour
    pet.motion.set_bounds((-800, -600, 0, 0))
    pet.place_for_focus(-400, -pet.height() if behaviour == 'floor' else -300)
    origin = pet.center()
    controls = call_controls(page, pet)
    if activity == 'light':
        QTest.keyClick(controls.interaction, Qt.Key.Key_Up)
    assert controls.interaction.currentData() == activity
    QTest.keyClick(controls.interact_button, Qt.Key.Key_Space)
    marker = pet._toy
    assert marker.target == (origin[0] - 80, -16 if behaviour == 'floor' else origin[1] - 40)
    assert other._toy is None
    assert marker.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus
    controls.refresh()
    assert controls.interaction.currentData() == activity
    assert (controls.call_x.value(), controls.call_y.value()) == (-80, -40)
    for _ in range(1500):
        if pet._toy is None:
            break
        marker.tick(1 / 60)
        pet.move(*pet.motion.step())
    assert pet._toy is None
    assert pet.companion.action == ('greet' if activity == 'call' else 'play')
    assert pet.companion.growth.affection == 0
    pet.profile_session.advance(0.75 if activity == 'call' else 3)
    assert pet.companion.growth.affection == (1 if activity == 'call' else 3)


def test_call_replacement_bounds_and_busy_preserve_current_interaction(social_pets):
    page, pets = social_pets
    pet = pets[0]
    pet.motion.behaviour = 'wander'
    pet.motion.set_bounds((-800, -600, 0, 0))
    pet.place_for_focus(-400, -300)
    controls = call_controls(page, pet)
    pet.start_light()
    previous = pet._toy
    controls.call_x.setValue(320)
    controls.call_y.setValue(320)
    QTest.keyClick(controls.interact_button, Qt.Key.Key_Space)
    marker = pet._toy
    assert marker is not previous and not previous.isVisible()
    x, y = marker.target
    assert (x - marker.origin[0]) ** 2 + (y - marker.origin[1]) ** 2 <= marker.radius ** 2 + 0.001
    assert -784 <= x <= -16 and -584 <= y <= -16
    pet._dragging = True
    QTest.keyClick(controls.interact_button, Qt.Key.Key_Space)
    assert pet._toy is marker
    pet._dragging = False
    pet.stop_toy()
    pet.profile_session.request('groom')
    QTest.keyClick(controls.interact_button, Qt.Key.Key_Space)
    assert pet._toy is None
    assert pet.companion.action == 'groom'
    pet.hide()
    QTest.keyClick(controls.interact_button, Qt.Key.Key_Space)
    assert not pet.isVisible() and pet._toy is None


def test_puppet_busy_call_preserves_care(puppet):
    from frontengine.ui.page.pet.pet_setting_ui import PetSettingUI
    page = PetSettingUI()
    try:
        controls = call_controls(page, puppet)
        puppet.profile_session.request('groom')
        before = puppet.profile_session.state()
        QTest.keyClick(controls.interact_button, Qt.Key.Key_Space)
        assert puppet.profile_session.state() == before
        assert puppet.profile_session.companion.action == 'groom'
        assert controls.status.text()
    finally:
        page.close()


@pytest.mark.parametrize('restriction', ['work', 'rest', 'settled'])
def test_keyboard_call_does_not_override_mode_or_settled_state(social_pets, restriction):
    page, pets = social_pets
    pet = pets[0]
    controls = call_controls(page, pet)
    if restriction == 'settled':
        pet.motion.settled = True
    else:
        pet.profile_session.set_mode(restriction)
    before = pet.profile_session.state()
    QTest.keyClick(controls.interact_button, Qt.Key.Key_Space)
    assert pet._toy is None
    assert pet.profile_session.state() == before
    assert pet.motion.settled == (restriction == 'settled')


def test_floor_call_vertical_offset_does_not_change_horizontal_destination(social_pets):
    _, pets = social_pets
    pet = pets[0]
    pet.motion.behaviour = 'floor'
    pet.motion.set_bounds((-800, -600, 0, 0))
    pet.place_for_focus(-400, -pet.height())
    targets = []
    for vertical in (0, -320, 320):
        assert pet.start_call(offset=(120, vertical)) == 'accepted'
        targets.append(pet._toy.target)
    assert targets[0] == targets[1] == targets[2]
