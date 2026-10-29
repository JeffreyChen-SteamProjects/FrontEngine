from PySide6.QtCore import Qt
import pytest
import test_pet_social_modes as fixtures

social_pets = fixtures.social_pets


def setup_ball(pet):
    pet.motion.set_bounds((0, 0, 800, 600))
    pet.place_for_focus(250, 600 - pet.height())
    pet.start_ball()
    assert pet._toy is not None
    return pet._toy


@pytest.mark.parametrize('behaviour', ['floor', 'wander', 'chase'])
def test_ball_full_round_returns_and_rewards_once(social_pets, behaviour):
    _, pets = social_pets
    pet = pets[0]
    pet.motion.behaviour = behaviour
    ball = setup_ball(pet)
    assert not pet.can_socialize
    assert ball.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus
    assert ball.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    phases = set()
    for _ in range(1800):
        if pet._toy is None:
            break
        phases.add(ball.phase)
        ball.tick(1 / 60)
        x, y = pet.motion.step()
        pet.move(x, y)
    assert {'flight', 'return'} <= phases
    assert pet._toy is None
    assert pet.companion.growth.affection == 1
    assert pet.motion.guidance is None
    assert pet.profile_session.reward('ball') == 'cooldown'


@pytest.mark.parametrize('interrupt', ['work', 'rest', 'pet', 'hide', 'settled', 'stop'])
def test_ball_interruption_clears_guidance_without_reward(social_pets, interrupt):
    _, pets = social_pets
    pet = pets[0]
    ball = setup_ball(pet)
    ball.tick(0.03)
    if interrupt in ('work', 'rest'):
        pet.profile_session.set_mode(interrupt)
    elif interrupt == 'pet':
        pet._request_interaction('pet')
    elif interrupt == 'hide':
        pet.hide()
    elif interrupt == 'settled':
        pet.motion.settled = True
        pet._on_tick()
    else:
        pet.stop_toy()
    assert pet._toy is None
    assert not ball.isVisible()
    assert pet.motion.guidance is None
    assert pet.companion.growth.affection == 0


def test_drag_release_rethrows_and_right_click_removes_ball(social_pets):
    from PySide6.QtCore import QEvent, QPointF
    from PySide6.QtGui import QMouseEvent

    _, pets = social_pets
    pet = pets[0]
    ball = setup_ball(pet)
    def event(kind, x, y, button, buttons):
        return QMouseEvent(kind, QPointF(14, 14), QPointF(x, y), button, buttons,
                           Qt.KeyboardModifier.NoModifier)
    left = Qt.MouseButton.LeftButton
    ball.mousePressEvent(event(QEvent.Type.MouseButtonPress, 300, 300, left, left))
    assert ball.dragging
    assert pet.motion.guidance is None
    ball.mouseMoveEvent(event(QEvent.Type.MouseMove, 450, 200, Qt.MouseButton.NoButton, left))
    assert (ball.xpos, ball.ypos) == (436, 186)
    ball.mouseReleaseEvent(event(QEvent.Type.MouseButtonRelease, 450, 200, left, Qt.MouseButton.NoButton))
    assert not ball.dragging
    assert ball.phase == 'flight'
    assert ball.vx > 0 and ball.vy < 0
    ball.tick(0.03)
    assert pet.motion.guidance is not None
    right = Qt.MouseButton.RightButton
    ball.mousePressEvent(event(QEvent.Type.MouseButtonPress, 450, 200, right, right))
    assert pet._toy is None
    assert pet.companion.growth.affection == 0


def test_ball_stays_in_negative_work_area_and_timeout_has_no_reward(social_pets):
    _, pets = social_pets
    pet = pets[0]
    pet.motion.set_bounds((-800, -600, 0, 0))
    pet.place_for_focus(-400, -200)
    pet.start_ball()
    ball = pet._toy
    ball.vx, ball.vy = -600, -600
    for _ in range(602):
        if pet._toy is None:
            break
        ball.tick(0.05)
        assert -800 <= ball.xpos <= -ball.width()
        assert -600 <= ball.ypos <= -ball.height()
    assert pet._toy is None
    assert pet.companion.growth.affection == 0


def test_ball_can_be_retrieved_from_a_window_perch(social_pets):
    _, pets = social_pets
    pet = pets[0]
    pet.motion.set_bounds((0, 0, 800, 600))
    pet.place_for_focus(250, 150)
    pet.motion.on_platform = True
    pet.motion.platform_span = (240, 400)
    pet.motion.ground_feet = 150 + pet.height()
    pet.motion.set_platforms([(240, 400, 150 + pet.height()), (0, 800, 400)])
    pet.start_ball()
    ball = pet._toy
    assert not pet.motion.on_platform
    assert pet.motion.platforms == []
    for _ in range(1800):
        if pet._toy is None:
            break
        ball.tick(1 / 60)
        x, y = pet.motion.step()
        pet.move(x, y)
    assert pet._toy is None
    assert pet.companion.growth.affection == 1


def test_window_perches_refresh_after_ball_is_put_away(social_pets, monkeypatch):
    from frontengine.show.pet import desktop_pet

    _, pets = social_pets
    pet = pets[0]
    setup_ball(pet)
    pet._sit_on_windows = True
    calls = []
    monkeypatch.setattr(desktop_pet, 'windows_platforms',
                        lambda **kwargs: calls.append(kwargs) or [(0, 800, 300)])
    pet._platform_tick = 9
    pet._on_tick()
    assert calls == []
    pet.stop_toy()
    pet._on_tick()
    assert len(calls) == 1
    assert pet.motion.platforms == [(0, 800, 300)]
