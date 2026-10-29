import pytest
from PySide6.QtCore import Qt

import test_pet_social_modes as fixtures

social_pets = fixtures.social_pets


def start(pet):
    pet.motion.set_bounds((-800, -600, 0, 0))
    pet.place_for_focus(-600, -pet.height())
    pet.come_action.trigger()
    return pet._toy


@pytest.mark.parametrize('behaviour', ['floor', 'wander', 'chase'])
def test_call_reaches_marker_then_greets_with_shared_cooldown(social_pets, behaviour):
    _, pets = social_pets
    pet = pets[0]
    pet.motion.behaviour = behaviour
    marker = start(pet)
    assert marker.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus
    assert marker.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    assert not pet.can_socialize
    for _ in range(1500):
        if pet._toy is None:
            break
        marker.tick(1 / 60)
        x, y = pet.motion.step()
        pet.move(x, y)
    assert pet._toy is None
    assert pet.motion.guidance is None
    assert pet.companion.action == 'greet'
    assert pet.companion.growth.affection == 0
    pet.profile_session.advance(0.75)
    assert pet.companion.growth.affection == 1
    assert pet.profile_session.request('greet') == 'cooldown'


@pytest.mark.parametrize('interrupt', ['cancel', 'work', 'rest', 'hide', 'feed', 'toy'])
def test_call_interruption_clears_destination_without_reward(social_pets, interrupt):
    _, pets = social_pets
    pet = pets[0]
    marker = start(pet)
    marker.tick(0.05)
    if interrupt in ('work', 'rest'):
        pet.profile_session.set_mode(interrupt)
    elif interrupt == 'hide':
        pet.hide()
    elif interrupt == 'feed':
        pet.feed()
    elif interrupt == 'toy':
        pet.start_ball()
    else:
        pet.companion_actions['cancel'].trigger()
    assert pet._toy is not marker
    assert not marker.isVisible()
    assert pet.motion.guidance is None
    assert pet.companion.growth.affection == 0


def test_call_drag_target_is_bounded_and_timeout_cancels(social_pets):
    from PySide6.QtCore import QEvent, QPointF
    from PySide6.QtGui import QMouseEvent
    _, pets = social_pets
    pet = pets[0]
    marker = start(pet)
    left = Qt.MouseButton.LeftButton
    marker.mousePressEvent(QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(16, 16),
        QPointF(*marker.target), left, left, Qt.KeyboardModifier.NoModifier))
    marker.mouseMoveEvent(QMouseEvent(QEvent.Type.MouseMove, QPointF(16, 16),
        QPointF(10000, 10000), Qt.MouseButton.NoButton, left, Qt.KeyboardModifier.NoModifier))
    x, y = marker.target
    assert -784 <= x <= -16 and -584 <= y <= -16
    for _ in range(601):
        if pet._toy is not None:
            marker.tick(0.05)
    assert pet._toy is None
    assert pet.companion.action is None
    assert pet.companion.growth.affection == 0
