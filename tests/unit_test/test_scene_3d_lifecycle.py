"""Screen loss and performance changes preserve the shared scene's user intent."""
import wave
import weakref
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QObject, Signal, QRect
from PySide6.QtGui import QColor, QImage

from frontengine.show.scene.runtime3d import Scene3DRuntime
from frontengine.show.scene.screen_topology import SceneScreenTopology
from frontengine.utils.scene_format.scene_3d_document import make_3d_scene


def test_undo_history_releases_its_document_without_a_native_ownership_cycle():
    from shiboken6 import isValid
    from frontengine.utils.scene_format.scene_editor_document import SceneEditorDocument
    document = SceneEditorDocument()
    document.reset(make_3d_scene({'cube': {'type': 'CUBE'}}))
    document.update('cube', {'opacity': 75})
    command = document.undo.command(0)
    reference = weakref.ref(document)
    del document
    try:
        assert reference() is None
        assert not isValid(command)
    finally:
        if reference() is not None:
            reference().undo.clear()


def test_crossfade_does_not_finish_an_open_ended_scene():
    from frontengine.show.scene.view3d import Scene3DView
    runtime = Scene3DRuntime(make_3d_scene(), {})
    now = [0.]
    runtime.timeline.clock = lambda: now[0]
    runtime.set_owner('visible', True)
    image = QImage(16, 16, QImage.Format.Format_RGBA8888)
    image.fill(QColor('blue'))
    view = SimpleNamespace(runtime=runtime, timeline=runtime.timeline, viewport=SimpleNamespace())
    try:
        Scene3DView.begin_transition(view, image)
        now[0] = 1.
        runtime.timeline.tick()
        assert runtime.timeline.duration == 0
        assert runtime.timeline.state == 'playing' and runtime.timeline.requested
        assert runtime.timeline.position == 1.
    finally:
        runtime.close()


class Screen(QObject):
    availableGeometryChanged = Signal(object)
    def __init__(self, name, serial):
        super().__init__()
        self.label, self.serial = name, serial
    def name(self): return self.label
    def serialNumber(self): return self.serial
    def manufacturer(self): return 'Test'
    def model(self): return 'Owned fixture'
    def availableGeometry(self): return QRect(0, 0, 640, 480)


class Application(QObject):
    screenRemoved = Signal(object)
    screenAdded = Signal(object)
    primaryScreenChanged = Signal(object)
    def __init__(self, screens):
        super().__init__()
        self.targets = screens
    def screens(self): return self.targets
    def primaryScreen(self): return self.targets[0] if self.targets else None


class View(QObject):
    closed = Signal()
    def __init__(self, runtime):
        super().__init__()
        self.runtime, self.visible, self.disposed, self.target = runtime, False, False, None
        self.primes = 0
    def setScreen(self, screen): self.target = screen
    def move(self, _point): pass
    def prime(self): self.primes += 1
    def isVisible(self): return self.visible
    def showMaximized(self):
        self.visible = True
        self.runtime.set_owner(id(self), True)
    def hide(self):
        self.visible = False
        self.runtime.set_owner(id(self), False)
    def close(self):
        self.hide()
        self.disposed = True
        self.closed.emit()


@pytest.fixture
def topology():
    runtime = Scene3DRuntime(make_3d_scene(), {})
    first, second = Screen('Display 1', 'one'), Screen('Display 2', 'two')
    app = Application([first, second])
    views = [View(runtime), View(runtime)]
    for view in views: view.showMaximized()
    runtime.timeline.duration = 10
    runtime.timeline.play()
    controller = SceneScreenTopology(runtime, app.targets, views, application=app,
                                      view_factory=View, alive=lambda view: not view.disposed)
    runtime.topology = controller
    controller.start(views)
    try:
        yield runtime, controller, app, first, second, views
    finally:
        runtime.close()


def test_screen_loss_keeps_other_view_and_all_loss_suspends_shared_clock(topology):
    runtime, controller, app, first, second, views = topology
    old_first, old_second = views
    app.targets.remove(first)
    app.screenRemoved.emit(first)
    assert views == [old_second] and old_first.disposed
    assert runtime.timeline.active and runtime.timeline.requested
    app.targets.remove(second)
    app.screenRemoved.emit(second)
    assert not views and not runtime.timeline.active and runtime.timeline.requested
    held = runtime.timeline.position
    replacement = Screen('Display 7', 'one')
    app.targets.append(replacement)
    app.screenAdded.emit(replacement)
    assert len(views) == 1 and views[0].target is replacement and views[0].primes == 1
    assert runtime.timeline.position == held and runtime.timeline.active and runtime.timeline.requested
    app.screenAdded.emit(replacement)
    assert len(views) == 1 and len(runtime.owners) == 1


def test_pause_and_hide_all_survive_reconnection(topology):
    runtime, controller, app, first, _second, views = topology
    runtime.timeline.pause()
    controller.set_group_hidden(True)
    app.targets.remove(first)
    app.screenRemoved.emit(first)
    replacement = Screen('Renamed', 'one')
    app.targets.append(replacement)
    app.screenAdded.emit(replacement)
    assert all(not view.isVisible() for view in views)
    assert not runtime.timeline.active
    controller.set_group_hidden(False)
    assert runtime.timeline.active and not runtime.timeline.requested
    assert runtime.timeline.state == 'paused'


def test_manually_closed_views_and_stopped_scenes_do_not_reopen(topology):
    runtime, controller, app, first, _second, views = topology
    view = views[0]
    view.close()
    assert len(views) == 1
    app.targets.remove(first)
    app.screenRemoved.emit(first)
    app.targets.append(first)
    app.screenAdded.emit(first)
    assert len(views) == 1
    controller.close()
    before = list(views)
    app.screenAdded.emit(Screen('New', 'one'))
    assert views == before


def test_reconnection_failure_preserves_other_targets(topology):
    runtime, controller, app, first, _second, views = topology
    errors = []
    runtime.failed.connect(errors.append)
    app.targets.remove(first)
    app.screenRemoved.emit(first)
    survivor = views[0]
    class FailingView(View):
        def prime(self): raise RuntimeError('GPU context lost')
    controller.view_factory = FailingView
    app.targets.append(first)
    app.screenAdded.emit(first)
    assert views == [survivor] and runtime.timeline.active
    assert any('GPU context lost' in error for error in errors)
    controller.view_factory = View
    controller.retry()
    assert len(views) == 2


def test_quality_and_power_propagate_without_changing_playback_time(tmp_path):
    path = tmp_path/'silence.wav'
    with wave.open(str(path), 'wb') as stream:
        stream.setparams((1, 2, 8000, 0, 'NONE', 'not compressed'))
        stream.writeframes(b'\0\0'*800)
    runtime = Scene3DRuntime(make_3d_scene({'sound': {'type': 'SOUND', 'file_path': str(path)}}), {})
    try:
        runtime.timeline.duration = 10
        runtime.timeline.seek(3)
        runtime.timeline.pause()
        runtime.set_quality_tier('saver')
        runtime.set_low_power(True)
        source = runtime.sources['sound'].widget
        assert source.quality_tier == 'saver' and source.low_power
        assert source.timer.interval() == 250 and runtime.timeline.timer.interval() == 250
        assert runtime.render_scale == .6
        assert runtime.timeline.position == 3 and not runtime.timeline.requested
        image = QImage(1280, 1280, QImage.Format.Format_RGBA8888)
        image.fill(QColor('red'))
        source.set_frame(image)
        assert source.frame.width() == 768
        runtime.set_low_power(False)
        runtime.set_quality_tier('high')
        assert runtime.timeline.timer.interval() == 16 and source.timer.interval() == 16
        assert runtime.render_scale == 1 and runtime.timeline.position == 3
    finally:
        runtime.close()
