"""A Puppet click greets on release; a drag past the platform distance moves it without rewards."""
from PySide6.QtCore import QCoreApplication, QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

import test_puppet_petting as fixtures

puppet = fixtures.puppet


def _send(pet, kind, local, buttons):
    global_point = QPointF(pet.mapToGlobal(local.toPoint()))
    button = Qt.MouseButton.LeftButton if kind != QEvent.Type.MouseMove else Qt.MouseButton.NoButton
    event = QMouseEvent(kind, local, global_point, button, buttons, Qt.KeyboardModifier.NoModifier)
    QCoreApplication.sendEvent(pet.canvas, event)


def _press(pet, point):
    _send(pet, QEvent.Type.MouseButtonPress, point, Qt.MouseButton.LeftButton)


def _move(pet, point):
    _send(pet, QEvent.Type.MouseMove, point, Qt.MouseButton.LeftButton)


def _release(pet, point):
    _send(pet, QEvent.Type.MouseButtonRelease, point, Qt.MouseButton.NoButton)


def test_click_greets_on_release_and_press_alone_grants_nothing(puppet):
    affection = puppet.profile_session.companion.growth.affection
    _press(puppet, QPointF(40, 40))
    assert puppet.profile_session.companion.action is None
    assert puppet.profile_session.companion.growth.affection == affection
    _release(puppet, QPointF(40, 40))
    assert puppet.profile_session.companion.action == 'greet'


def test_small_jitter_neither_moves_nor_drags(puppet):
    start = puppet.pos()
    _press(puppet, QPointF(40, 40))
    _move(puppet, QPointF(40 + max(0, QApplication.startDragDistance() - 2), 40))
    assert puppet.pos() == start
    assert puppet.profile_session.companion.action is None
    _release(puppet, QPointF(41, 40))
    assert puppet.profile_session.companion.action == 'greet'


def test_drag_moves_without_greeting_or_reward(puppet):
    start = puppet.pos()
    affection = puppet.profile_session.companion.growth.affection
    revision = puppet.placement_revision
    _press(puppet, QPointF(40, 40))
    _move(puppet, QPointF(40 + QApplication.startDragDistance() + 30, 40))
    assert puppet.profile_session.companion.action == 'drag'
    assert puppet.pos() != start
    assert puppet.placement_revision > revision
    _release(puppet, QPointF(40 + QApplication.startDragDistance() + 30, 40))
    assert puppet.profile_session.companion.action is None
    puppet.profile_session.advance(5)
    assert puppet.profile_session.companion.growth.affection == affection


def test_click_greeting_uses_the_bond_line_and_goodbye_is_scheduled(puppet, monkeypatch):
    from frontengine.show.pet import puppet_pet
    from frontengine.utils.multi_language.retranslate import translate
    lines, scheduled = [], []
    monkeypatch.setattr(puppet, 'say', lambda text=None: lines.append(text))
    puppet.profile_session.companion.growth.affection = 150
    _press(puppet, QPointF(40, 40))
    _release(puppet, QPointF(40, 40))
    assert lines[-1] == translate('pet_greet_close')

    class Timer:
        @staticmethod
        def singleShot(delay, receiver, callback):
            scheduled.append((delay, receiver, callback))
    monkeypatch.setattr(puppet_pet, 'QTimer', Timer)
    puppet.say_goodbye()
    puppet.say_goodbye()
    assert lines[-1] == translate('pet_goodbye')
    assert len(scheduled) == 1 and scheduled[0][0] == 900 and scheduled[0][1] is puppet


def test_chatter_off_silences_scheduled_script_lines(puppet, monkeypatch):
    lines = []
    monkeypatch.setattr(puppet, 'say', lambda text=None: lines.append(text))
    monkeypatch.setattr(puppet.script, 'due_scheduled_message', lambda: 'Stretch time!')
    puppet._script_tick()
    assert lines == ['Stretch time!']
    before = puppet.profile_session.companion.preferences
    values = {**puppet._presentation_defaults, 'chatter': 'off'}
    puppet.profile_session.apply_preferences(before, {**before, 'presentation': values})
    puppet._script_tick()
    assert lines == ['Stretch time!']
    assert 'chatter' in puppet.customization_fields and 'motion' not in puppet.customization_fields
