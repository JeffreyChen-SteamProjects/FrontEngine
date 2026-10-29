from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent

from frontengine.utils.pet_companion.petting import PettingGesture
import test_pet_social_modes as fixtures

social_pets = fixtures.social_pets


def move(pet, x):
    point = QPointF(x, 20)
    event = QMouseEvent(QEvent.Type.MouseMove, point, point,
                        Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton,
                        Qt.KeyboardModifier.NoModifier)
    pet.mouseMoveEvent(event)


def stroke(pet):
    for x in (20, 50, 20, 50):
        move(pet, x)


def test_jitter_and_one_direction_are_not_petting():
    gesture = PettingGesture(10)
    assert not any(gesture.move(x, 0) for x in (0, 1, 2, 1, 0, 10, 20, 30))
    assert not gesture.move(20, 0)
    assert gesture.move(30, 0)


def test_menu_arms_strokes_without_dragging_or_immediate_reward(social_pets):
    _, pets = social_pets
    pet = pets[0]
    position = pet.pos()
    pet.companion_actions['pet'].trigger()
    assert pet.companion.action is None
    assert not pet.can_socialize
    stroke(pet)
    assert pet.companion.action == 'pet'
    assert not pet._dragging
    assert pet.pos() == position
    assert pet.companion.growth.affection == 0
    pet.profile_session.advance(2)
    assert pet.companion.growth.affection == 2
    stroke(pet)
    pet.profile_session.advance(2)
    assert pet.companion.growth.affection == 2
    pet.companion_actions['cancel'].trigger()
    assert pet._petting is None


def test_leaving_or_changing_mode_cancels_unfinished_stroke(social_pets):
    _, pets = social_pets
    pet = pets[0]
    for interrupt in (lambda: pet.leaveEvent(QEvent(QEvent.Type.Leave)),
                      lambda: pet.profile_session.set_mode('work'), pet.hide):
        pet.show()
        pet._request_interaction('pet')
        stroke(pet)
        assert pet.companion.action == 'pet'
        interrupt()
        assert pet._petting is None
        pet.profile_session.advance(3)
        assert pet.companion.growth.affection == 0


def test_feeding_interrupts_unfinished_petting_without_petting_reward(social_pets):
    _, pets = social_pets
    pet = pets[0]
    pet._request_interaction('pet')
    stroke(pet)
    assert pet.companion.action == 'pet'
    pet.feed('music')
    assert pet.companion.action == 'feed'
    assert pet._petting is None
    pet.profile_session.advance(2)
    assert pet.companion.growth.affection == 5
