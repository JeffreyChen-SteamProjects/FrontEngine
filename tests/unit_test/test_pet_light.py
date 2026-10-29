from math import hypot

import pytest
from PySide6.QtCore import Qt
import test_pet_social_modes as fixtures

social_pets = fixtures.social_pets


def start(pet):
    pet.motion.set_bounds((0, 0, 800, 600))
    pet.place_for_focus(200, 600 - pet.height())
    pet.light_action.trigger()
    return pet._toy


@pytest.mark.parametrize('behaviour', ['floor', 'wander', 'chase'])
def test_reaching_light_starts_play_and_rewards_only_on_completion(social_pets, behaviour):
    _, pets = social_pets
    pet = pets[0]
    pet.motion.behaviour = behaviour
    light = start(pet)
    assert light.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus
    assert not pet.can_socialize
    for _ in range(1500):
        if pet._toy is None:
            break
        light.tick(1 / 60)
        x, y = pet.motion.step()
        pet.move(x, y)
    assert pet._toy is None
    assert pet.companion.action == 'play'
    assert pet.companion.growth.affection == 0
    pet.profile_session.advance(3)
    assert pet.companion.growth.affection == 3
    assert pet.profile_session.request('play') == 'cooldown'


def test_light_bounds_and_mutually_exclusive_toys(social_pets):
    _, pets = social_pets
    pet = pets[0]
    pet.motion.behaviour = 'wander'
    light = start(pet)
    light.place_target(5000, -5000)
    assert hypot(light.target[0] - light.origin[0], light.target[1] - light.origin[1]) <= light.radius + 0.01
    assert 16 <= light.target[0] <= 784
    assert 16 <= light.target[1] <= 584
    pet.start_ball()
    assert not light.isVisible()
    ball = pet._toy
    pet.start_light()
    assert not ball.isVisible()
    assert pet._toy is not ball
    pet.ball_stop_action.trigger()
    assert pet._toy is None


@pytest.mark.parametrize('interrupt', ['work', 'rest', 'pet', 'hide', 'settled'])
def test_light_cancellation_never_rewards(social_pets, interrupt):
    _, pets = social_pets
    pet = pets[0]
    light = start(pet)
    light.tick(0.05)
    if interrupt in ('work', 'rest'):
        pet.profile_session.set_mode(interrupt)
    elif interrupt == 'pet':
        pet._request_interaction('pet')
    elif interrupt == 'hide':
        pet.hide()
    else:
        pet.motion.settled = True
        pet._on_tick()
    assert pet._toy is None
    assert pet.motion.guidance is None
    pet.profile_session.advance(3)
    assert pet.companion.growth.affection == 0


def test_dragged_light_waits_for_release_and_times_out(social_pets):
    from PySide6.QtCore import QEvent, QPointF
    from PySide6.QtGui import QMouseEvent

    _, pets = social_pets
    pet = pets[0]
    light = start(pet)
    def event(kind, button, buttons):
        return QMouseEvent(kind, QPointF(16, 16), QPointF(*pet.center()),
                           button, buttons, Qt.KeyboardModifier.NoModifier)
    left = Qt.MouseButton.LeftButton
    light.mousePressEvent(event(QEvent.Type.MouseButtonPress, left, left))
    light.mouseMoveEvent(event(QEvent.Type.MouseMove, Qt.MouseButton.NoButton, left))
    for _ in range(20):
        light.tick(0.05)
    assert pet.companion.action is None
    light.mouseReleaseEvent(event(QEvent.Type.MouseButtonRelease, left, Qt.MouseButton.NoButton))
    for _ in range(11):
        if pet._toy is not None:
            light.tick(0.05)
    assert pet.companion.action == 'play'
    pet.profile_session.request('cancel')
    pet.start_light()
    light = pet._toy
    light.place_target(780, 580)
    for _ in range(601):
        if pet._toy is not None:
            light.tick(0.05)
    assert pet._toy is None
    assert pet.companion.growth.affection == 0
