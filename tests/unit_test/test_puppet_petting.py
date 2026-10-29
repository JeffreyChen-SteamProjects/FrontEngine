import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QContextMenuEvent, QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QMenu

from test_puppet_startup_lifecycle import asset
from frontengine.utils.multi_language.retranslate import translate


@pytest.fixture
def puppet(tmp_path):
    pytest.importorskip('Imervue.puppet.document_io')
    from frontengine.show.pet.puppet_pet import PuppetPetWidget
    from frontengine.user_setting.pet_profiles import PetProfiles
    pet = PuppetPetWidget(asset(tmp_path), size=(128, 192), profiles=PetProfiles({}, lambda: None))
    pet.show()
    yield pet
    pet.close()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def command(pet, monkeypatch, name):
    class Menu(QMenu):
        def exec(self, *args):
            next(action for action in self.actions()
                 if action.text() == translate('pet_companion_' + name)).trigger()
    monkeypatch.setattr('frontengine.show.pet.puppet_pet.QMenu', Menu)
    pet.contextMenuEvent(QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(10, 10), QPoint(10, 10)))


def stroke(pet):
    for x in (20, 60, 20, 60):
        point = QPointF(x, 30)
        event = QMouseEvent(QEvent.Type.MouseMove, point, point,
                            Qt.MouseButton.NoButton, Qt.MouseButton.NoButton,
                            Qt.KeyboardModifier.NoModifier)
        QCoreApplication.sendEvent(pet.canvas, event)


def test_menu_waits_for_strokes_and_rewards_only_completed_care(puppet, monkeypatch):
    command(puppet, monkeypatch, 'pet')
    session = puppet.profile_session
    assert session.companion.action is None
    position = puppet.pos()
    stroke(puppet)
    assert session.companion.action == 'pet'
    assert puppet.pos() == position
    assert session.companion.growth.affection == 0
    session.advance(2)
    assert session.companion.growth.affection == 2
    stroke(puppet)
    session.advance(2)
    assert session.companion.growth.affection == 2


@pytest.mark.parametrize('interrupt', ['leave', 'hide', 'mode', 'cancel', 'settle'])
def test_interruption_cancels_unfinished_petting(puppet, monkeypatch, interrupt):
    command(puppet, monkeypatch, 'pet')
    stroke(puppet)
    assert puppet.profile_session.companion.action == 'pet'
    if interrupt == 'leave':
        QCoreApplication.sendEvent(puppet.canvas, QEvent(QEvent.Type.Leave))
    elif interrupt == 'hide':
        puppet.hide()
    elif interrupt == 'mode':
        puppet.profile_session.set_mode('work')
    elif interrupt == 'settle':
        puppet.set_settled(True)
    else:
        command(puppet, monkeypatch, 'cancel')
    puppet.profile_session.advance(3)
    assert puppet.profile_session.companion.growth.affection == 0
    stroke(puppet)
    assert puppet.profile_session.companion.action is None


def test_petting_consumes_clicks_and_escape_without_drag_hit_or_close(puppet, monkeypatch):
    command(puppet, monkeypatch, 'pet')
    hits = []
    puppet.canvas.hit_area_triggered.connect(hits.append)
    for kind in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease,
                 QEvent.Type.MouseButtonDblClick):
        point = QPointF(30, 30)
        event = QMouseEvent(kind, point, point, Qt.MouseButton.LeftButton,
                            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        assert puppet.eventFilter(puppet.canvas, event)
    assert puppet._drag_origin is None
    assert hits == []
    stroke(puppet)
    event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    puppet.keyPressEvent(event)
    assert puppet.isVisible()
    assert puppet._petting is None
    assert puppet.profile_session.companion.action is None


def test_feed_and_manual_motion_release_gesture(puppet, monkeypatch):
    for interrupt in (puppet.feed, lambda: puppet.play_motion('unknown')):
        puppet.profile_session.request('cancel')
        command(puppet, monkeypatch, 'pet')
        original_tracking = puppet._petting_tracking
        interrupt()
        assert puppet._petting is None
        assert puppet.canvas.hasMouseTracking() == original_tracking


def test_recovery_ends_armed_gesture(puppet, monkeypatch):
    from frontengine.show.pet.recovery import recover_pet
    command(puppet, monkeypatch, 'pet')
    recover_pet(puppet, puppet.screen())
    stroke(puppet)
    assert puppet._petting is None
    assert puppet.profile_session.companion.action is None
