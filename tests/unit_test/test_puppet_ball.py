import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QContextMenuEvent, QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMenu

import test_puppet_petting as fixtures
import test_pet_social_modes as sprite_fixtures
from test_puppet_call import prepare
from test_pet_keyboard_call import call_controls
from frontengine.utils.multi_language.retranslate import translate

puppet = fixtures.puppet
social_pets = sprite_fixtures.social_pets


@pytest.mark.parametrize('size', [(16, 16), (320, 480)])
@pytest.mark.parametrize('corner', ['top_left', 'top_right', 'bottom_left', 'bottom_right'])
def test_puppet_ball_returns_to_original_center_from_work_area_corners(puppet, monkeypatch, size, corner):
    prepare(puppet, monkeypatch)
    puppet._initial_size = size
    puppet.resize(*size)
    puppet.move(-1000 if corner.endswith('left') else -size[0],
                -800 if corner.startswith('top') else -size[1])
    origin = puppet.center()
    assert puppet.start_ball() == 'accepted'
    ball = puppet._target.marker
    assert ball.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus
    assert ball.accessibleName() == translate('pet_ball_start')
    phases = set()
    area = QRect(-1000, -800, 1000, 800)
    for _ in range(1801):
        if puppet._target.marker is None:
            break
        phases.add(ball.phase)
        puppet._target.tick(1 / 60)
        assert area.contains(puppet.geometry())
        assert area.contains(ball.geometry())
    assert {'flight', 'return'} <= phases
    assert puppet._target.marker is None
    assert not puppet._target.timer.isActive()
    assert puppet._target._guidance is None
    assert abs(puppet.center()[0] - origin[0]) <= 2
    assert abs(puppet.center()[1] - origin[1]) <= 2
    assert puppet.profile_session.companion.growth.affection == 1
    assert puppet.profile_session.reward('ball') == 'cooldown'


def pointer_event(kind, ball, button, buttons):
    return QMouseEvent(kind, QPointF(14, 14), QPointF(ball.xpos + 14, ball.ypos + 14),
                       button, buttons, Qt.KeyboardModifier.NoModifier)


def test_ball_drag_pauses_pet_and_rethrow_owns_new_timeout(puppet, monkeypatch):
    prepare(puppet, monkeypatch)
    puppet.start_ball()
    ball = puppet._target.marker
    puppet._target.tick(0.05)
    left = Qt.MouseButton.LeftButton
    ball.mousePressEvent(pointer_event(QEvent.Type.MouseButtonPress, ball, left, left))
    position = puppet.pos()
    for _ in range(580):
        puppet._target.tick(0.05)
    assert puppet.pos() == position
    assert puppet._target._guidance is None
    ball.mouseReleaseEvent(pointer_event(QEvent.Type.MouseButtonRelease, ball, left, Qt.MouseButton.NoButton))
    assert ball._elapsed == 0
    ball.mousePressEvent(pointer_event(QEvent.Type.MouseButtonPress, ball, left, left))
    for _ in range(40):
        puppet._target.tick(0.05)
    assert puppet._target.marker is ball
    for _ in range(561):
        puppet._target.tick(0.05)
    assert puppet._target.marker is None
    assert puppet.profile_session.companion.growth.affection == 0


def test_ball_light_call_replace_each_other_and_busy_keeps_care(puppet, monkeypatch):
    prepare(puppet, monkeypatch)
    previous = None
    for activity in ('ball', 'light', 'ball', 'call', 'ball'):
        assert getattr(puppet, 'start_' + activity)() == 'accepted'
        assert puppet._target.marker is not previous
        if previous is not None:
            assert not previous.isVisible()
        previous = puppet._target.marker
    puppet.feed()
    assert puppet._target.marker is None
    before = puppet.profile_session.state()
    assert puppet.start_ball() == 'busy'
    assert puppet.profile_session.state() == before
    assert puppet.profile_session.companion.action == 'feed'


def test_puppet_ball_menu_and_keyboard_manager_entry(puppet, monkeypatch):
    from frontengine.ui.page.pet.pet_setting_ui import PetSettingUI
    prepare(puppet, monkeypatch)

    class Menu(QMenu):
        def exec(self, *_args):
            next(action for action in self.actions()
                 if action.text() == translate('pet_ball_start')).trigger()

    monkeypatch.setattr('frontengine.show.pet.puppet_pet.QMenu', Menu)
    puppet.contextMenuEvent(QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(10, 10), QPoint(10, 10)))
    assert puppet._target.marker.phase == 'flight'
    puppet.stop_toy()
    page = PetSettingUI()
    try:
        controls = call_controls(page, puppet)
        QTest.keyClick(controls.interaction, Qt.Key.Key_Up)
        QTest.keyClick(controls.interaction, Qt.Key.Key_Up)
        assert controls.interaction.currentData() == 'ball'
        assert not controls.call_x.isEnabled() and not controls.call_y.isEnabled()
        QTest.keyClick(controls.interact_button, Qt.Key.Key_Space)
        assert puppet._target.marker.phase == 'flight'
    finally:
        page.close()


def test_sprite_manager_ball_targets_selected_identity(social_pets):
    page, pets = social_pets
    controls = call_controls(page, pets[1])
    QTest.keyClick(controls.interaction, Qt.Key.Key_Up)
    QTest.keyClick(controls.interaction, Qt.Key.Key_Up)
    assert controls.interaction.currentData() == 'ball'
    QTest.keyClick(controls.interact_button, Qt.Key.Key_Space)
    assert pets[0]._toy is None
    assert pets[1]._toy.phase == 'flight'
