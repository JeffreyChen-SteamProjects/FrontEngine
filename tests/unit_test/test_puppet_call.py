import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QPointF, QRect, Qt
from PySide6.QtGui import QMouseEvent

import test_puppet_petting as fixtures

puppet = fixtures.puppet


def prepare(pet, monkeypatch):
    class Screen:
        def availableGeometry(self):
            return QRect(-1000, -800, 1000, 800)
    monkeypatch.setattr(pet, 'screen', lambda: Screen())
    pet._initial_size = (320, 480)
    pet.resize(*pet._initial_size)
    pet.move(-900, -650)
    assert not hasattr(pet, 'motion')


def test_large_puppet_moves_to_center_before_greeting(puppet, monkeypatch):
    prepare(puppet, monkeypatch)
    start = puppet.pos()
    assert puppet.start_call() == 'accepted'
    marker = puppet._target.marker
    assert puppet.geometry().contains(*map(round, marker.target))
    assert marker.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus
    assert marker.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    for _ in range(10):
        puppet._target.tick(0.05)
    assert puppet.x() > start.x()
    assert puppet.profile_session.companion.action is None
    assert puppet._target.marker is marker
    for _ in range(40):
        puppet._target.tick(0.05)
    assert puppet._target.marker is None
    assert not puppet._target.timer.isActive()
    assert puppet.profile_session.companion.action == 'greet'
    assert puppet.profile_session.companion.growth.affection == 0
    puppet.profile_session.advance(0.75)
    assert puppet.profile_session.companion.growth.affection == 1
    assert puppet.profile_session.request('greet') == 'cooldown'


@pytest.mark.parametrize('interrupt', [
    'work', 'rest', 'play', 'feed', 'pet', 'groom', 'cancel', 'hide', 'settle',
    'motion', 'expression', 'resize', 'canvas_drag', 'window_drag', 'placement', 'close',
])
@pytest.mark.parametrize('activity', ['call', 'light', 'ball'])
def test_puppet_call_interruptions_dispose_target_without_reward(puppet, monkeypatch, interrupt, activity):
    prepare(puppet, monkeypatch)
    start = getattr(puppet, 'start_' + activity)
    assert (start() if activity == 'ball' else start(offset=(280, 0))) == 'accepted'
    marker = puppet._target.marker
    if interrupt in ('work', 'rest', 'play'):
        puppet.profile_session.set_mode(interrupt)
    elif interrupt in ('pet', 'groom', 'cancel'):
        puppet._request_interaction(interrupt)
    elif interrupt == 'feed':
        puppet.feed()
    elif interrupt == 'hide':
        puppet.hide()
    elif interrupt == 'settle':
        puppet.set_settled(True)
    elif interrupt == 'motion':
        puppet.play_motion('unknown')
    elif interrupt == 'expression':
        puppet._choose_expression('unknown', False)
    elif interrupt == 'resize':
        puppet.resize(321, 480)
        puppet._target.tick(0.05)
    elif interrupt in ('canvas_drag', 'window_drag'):
        event = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(30, 30),
                           QPointF(*puppet.center()), Qt.MouseButton.LeftButton,
                           Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        if interrupt == 'canvas_drag':
            QCoreApplication.sendEvent(puppet.canvas, event)
        else:
            puppet.mousePressEvent(event)
    elif interrupt == 'placement':
        puppet.place_for_focus(-500, -600)
    else:
        puppet.close()
    assert puppet._target.marker is None
    assert not puppet._target.timer.isActive()
    assert not marker.isVisible()
    assert puppet.profile_session.companion.growth.affection == 0


def test_puppet_call_limits_full_window_and_replaces_single_marker(puppet, monkeypatch):
    prepare(puppet, monkeypatch)
    puppet.move(-330, -490)
    assert puppet.start_call(offset=(320, 320)) == 'accepted'
    marker = puppet._target.marker
    marker.dragging = True
    for _ in range(100):
        puppet._target.tick(0.05)
        assert QRect(-1000, -800, 1000, 800).contains(puppet.geometry())
    assert puppet._target.marker is marker
    assert puppet.start_call(offset=(-80, -40)) == 'accepted'
    assert puppet._target.marker is not marker and not marker.isVisible()
    puppet._target.marker.dragging = True
    for _ in range(601):
        puppet._target.tick(0.05)
    assert puppet._target.marker is None
    assert not puppet._target.timer.isActive()
    assert puppet.profile_session.companion.growth.affection == 0


@pytest.mark.parametrize('activity', ['call', 'light'])
def test_puppet_manager_call_uses_keyboard_offsets(puppet, monkeypatch, activity):
    from frontengine.ui.page.pet.pet_setting_ui import PetSettingUI
    from test_pet_keyboard_call import call_controls
    from PySide6.QtTest import QTest
    prepare(puppet, monkeypatch)
    page = PetSettingUI()
    try:
        controls = call_controls(page, puppet)
        if activity == 'light':
            QTest.keyClick(controls.interaction, Qt.Key.Key_Up)
        assert controls.interaction.currentData() == activity
        origin = puppet.center()
        QTest.keyClick(controls.interact_button, Qt.Key.Key_Space)
        assert puppet._target.marker.target == (origin[0] - 80, origin[1] - 40)
        controls.interaction.setCurrentIndex(controls.interaction.findData('cancel'))
        QTest.keyClick(controls.interact_button, Qt.Key.Key_Space)
        assert puppet._target.marker is None
    finally:
        page.close()


@pytest.mark.parametrize('position,offset', [
    ((-1000, -800), (-320, -320)), ((-16, -800), (320, -320)),
    ((-1000, -16), (-320, 320)), ((-16, -16), (320, 320)),
])
def test_small_puppet_marker_stays_inside_work_area(puppet, monkeypatch, position, offset):
    prepare(puppet, monkeypatch)
    puppet._initial_size = (16, 16)
    puppet.resize(16, 16)
    puppet.move(*position)
    assert puppet.start_call(offset=offset) == 'accepted'
    assert QRect(-1000, -800, 1000, 800).contains(puppet._target.marker.geometry())
