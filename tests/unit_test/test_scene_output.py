"""Fixed output independent of desktop pixels, bounded sends and teardown."""
import threading
import time

import numpy
import pytest
from PySide6.QtCore import QEvent, QCoreApplication, Qt
from PySide6.QtGui import QColor, QImage, QScreen
from PySide6.QtWidgets import QApplication

from frontengine.show.scene.render_session import SceneRenderSession
from frontengine.utils.virtual_camera.frame_sender import FrameSender


def wait(predicate):
    deadline = time.monotonic() + 5
    while not predicate() and time.monotonic() < deadline:
        QApplication.processEvents()
        threading.Event().wait(.005)
    assert predicate()


def scene(tmp_path):
    image = QImage(32, 32, QImage.Format.Format_RGBA8888)
    image.fill(QColor('red'))
    path = tmp_path / 'image.png'
    image.save(str(path))
    return {'image': {'type': 'IMAGE', 'file_path': str(path), 'width': 32, 'height': 32, 'opacity': 100}}


def test_snapshot_never_grabs_desktop_and_survives_window_position_changes(tmp_path, monkeypatch):
    def forbidden(*_args):
        raise AssertionError('Scene output must never capture desktop pixels')
    monkeypatch.setattr(QScreen, 'grabWindow', forbidden)
    entries = scene(tmp_path)
    session = SceneRenderSession(entries, (640, 480))
    try:
        before = session.frame()
        assert before.width() == 640 and before.height() == 480 and before.devicePixelRatio() == 1
        assert before.pixelColor(10, 10) == QColor('red')
        session.view.move(10000, 10000)
        entries['image']['x'] = 200
        assert session.frame() == before
        assert session.view.testAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        huge = QImage(1280, 960, QImage.Format.Format_RGBA8888)
        huge.fill(QColor('red'))
        huge.setDevicePixelRatio(2)
        monkeypatch.setattr(session.view, 'output_frame', lambda: huge)
        fixed = session.frame()
        assert fixed.width() == 640 and fixed.height() == 480 and fixed.devicePixelRatio() == 1
    finally:
        session.close()
    assert session.closed and session.frame().isNull() and not session.manager.widget_list


@pytest.mark.parametrize('size', [(0, 0), (True, 480), (640, 481), (3840, 2160)])
def test_bad_fixed_sizes_are_rejected(tmp_path, size):
    with pytest.raises(ValueError):
        SceneRenderSession(scene(tmp_path), size)


def test_missing_invalid_or_excessive_sources_close_partial_renderers(tmp_path):
    entries = scene(tmp_path)
    entries['image']['file_path'] = str(tmp_path / 'missing.png')
    with pytest.raises(ValueError, match='invalid'):
        SceneRenderSession(entries, (640, 480))
    entries = scene(tmp_path)
    entries['image'].update(width=8192, height=8192)
    with pytest.raises(ValueError, match='budget'):
        SceneRenderSession(entries, (640, 480))
    with pytest.raises(ValueError, match='eight'):
        SceneRenderSession({str(i): {'type': 'WEB', 'url': 'about:blank'} for i in range(9)}, (640, 480))


class Camera:
    def __init__(self, *_args):
        self.device, self.last_error = 'Injected camera', ''
        self.sent, self.closed = [], False

    def start(self):
        return True

    def send(self, pixels):
        self.sent.append(pixels.copy())
        return True

    def stop(self):
        self.closed = True


def test_blocked_device_retains_one_latest_frame_and_stop_does_not_wait():
    entered, release = threading.Event(), threading.Event()
    camera = Camera()
    def slow(pixels):
        entered.set()
        assert release.wait(5)
        camera.sent.append(pixels.copy())
        return True
    camera.send = slow
    sender = FrameSender(640, 480, 20, factory=lambda *_args: camera)
    sender.start()
    assert sender.submit(numpy.zeros((480, 640, 3), numpy.uint8))
    assert entered.wait(5)
    try:
        for value in range(100):
            sender.submit(numpy.full((480, 640, 3), value, numpy.uint8))
        assert sender.pending[0, 0, 0] == 99 and sender.dropped == 99
        before = time.monotonic()
        sender.stop()
        assert time.monotonic() - before < .1 and sender.pending is None
    finally:
        release.set()
        sender.thread.join(5)
    assert camera.closed and not sender.thread.is_alive()
    assert len(camera.sent) == 1


def test_failed_device_reports_reason_and_closes():
    camera = Camera()
    camera.start = lambda: False
    camera.last_error = 'Driver unavailable'
    sender = FrameSender(640, 480, 20, factory=lambda *_args: camera)
    errors = []
    sender.failed.connect(errors.append, Qt.ConnectionType.QueuedConnection)
    sender.start()
    wait(lambda: bool(errors))
    sender.thread.join(5)
    assert errors == ['Driver unavailable'] and camera.closed


def test_output_dialog_scene_edits_reject_and_page_shutdown_stop_all_output(tmp_path):
    from frontengine.ui.dialog.scene_output_dialog import SceneOutputDialog
    from frontengine.utils.scene_format.scene_editor_document import SceneEditorDocument
    document = SceneEditorDocument()
    document.reset(scene(tmp_path))
    cameras = []
    def sender_factory(width, height, fps, parent):
        camera = Camera()
        cameras.append(camera)
        return FrameSender(width, height, fps, parent, factory=lambda *_args: camera)
    dialog = SceneOutputDialog(document, sender_factory=sender_factory)
    dialog.show()
    dialog.start_preview()
    assert dialog.session is not None and not cameras
    dialog.send_camera()
    wait(lambda: cameras and cameras[0].sent)
    document.update('image', {'x': 50})
    wait(lambda: cameras[0].closed and not dialog.stopping_senders)
    assert dialog.session is None and dialog.preview.pixmap().isNull()
    dialog.start_preview()
    active = dialog.session
    dialog.reject()
    assert active.closed and dialog.session is None and not dialog.timer.isActive()
    dialog.close()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
