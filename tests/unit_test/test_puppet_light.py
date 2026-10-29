from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QContextMenuEvent, QMouseEvent
from PySide6.QtWidgets import QMenu

import test_puppet_petting as fixtures
from test_puppet_call import prepare
from frontengine.utils.multi_language.retranslate import translate

puppet = fixtures.puppet


def reach(pet):
    for _ in range(100):
        if pet._target.marker is None:
            return
        pet._target.tick(0.05)
    assert pet._target.marker is None


def test_puppet_light_rewards_completed_play_and_respects_cooldown(puppet, monkeypatch):
    prepare(puppet, monkeypatch)
    assert puppet.start_light() == 'accepted'
    marker = puppet._target.marker
    assert marker.appearance == 'light'
    assert marker.accessibleName() == translate('pet_light_start')
    assert marker.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus
    reach(puppet)
    assert puppet.profile_session.companion.action == 'play'
    assert puppet.profile_session.companion.growth.affection == 0
    puppet.profile_session.advance(3)
    assert puppet.profile_session.companion.growth.affection == 3
    assert puppet.start_light(offset=(0, 0)) == 'accepted'
    reach(puppet)
    assert puppet.profile_session.companion.action is None
    puppet.profile_session.advance(3)
    assert puppet.profile_session.companion.growth.affection == 3


def test_light_call_replacement_and_drag_wait_for_release(puppet, monkeypatch):
    prepare(puppet, monkeypatch)
    assert puppet.start_call() == 'accepted'
    call = puppet._target.marker
    assert puppet.start_light(offset=(0, 0)) == 'accepted'
    light = puppet._target.marker
    assert light is not call and not call.isVisible()
    left = Qt.MouseButton.LeftButton
    light.mousePressEvent(QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(16, 16),
        QPointF(*light.target), left, left, Qt.KeyboardModifier.NoModifier))
    for _ in range(20):
        puppet._target.tick(0.05)
    assert puppet._target.marker is light
    assert puppet.profile_session.companion.action is None
    light.mouseReleaseEvent(QMouseEvent(QEvent.Type.MouseButtonRelease, QPointF(16, 16),
        QPointF(*light.target), left, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))
    reach(puppet)
    assert puppet.profile_session.companion.action == 'play'
    puppet._request_interaction('cancel')
    assert puppet.profile_session.companion.growth.affection == 0
    puppet.start_light()
    light = puppet._target.marker
    puppet.start_call()
    assert puppet._target.marker is not light and not light.isVisible()
    assert puppet._target.arrival_action == 'greet'


def test_light_menu_start_stop_and_busy_preserves_care(puppet, monkeypatch):
    prepare(puppet, monkeypatch)
    selected = ['pet_light_start']

    class Menu(QMenu):
        def exec(self, *_args):
            next(action for action in self.actions()
                 if action.text() == translate(selected[0])).trigger()

    monkeypatch.setattr('frontengine.show.pet.puppet_pet.QMenu', Menu)
    event = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(10, 10), QPoint(10, 10))
    puppet.contextMenuEvent(event)
    assert puppet._target.marker.appearance == 'light'
    selected[0] = 'pet_toy_stop'
    puppet.contextMenuEvent(event)
    assert puppet._target.marker is None
    assert not puppet._target.timer.isActive()
    puppet.profile_session.request('groom')
    before = puppet.profile_session.state()
    assert puppet.start_light() == 'busy'
    assert puppet.profile_session.companion.action == 'groom'
    assert puppet.profile_session.state() == before
