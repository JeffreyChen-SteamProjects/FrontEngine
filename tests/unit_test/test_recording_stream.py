"""Recording must write live GIF frames and finalize without blocking Qt."""
import threading
import time

import numpy
import pytest
from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QImageReader, QMovie, QPixmap
from PySide6.QtWidgets import QApplication

from frontengine.utils.recording import gif_writer
from frontengine.utils.recording.frame_recorder import FrameRecorder


def wait_until(predicate):
    deadline = time.monotonic() + 5
    while not predicate() and time.monotonic() < deadline:
        QApplication.processEvents()
        threading.Event().wait(0.005)
    assert predicate()


def pixels(color, width=24, height=16):
    return numpy.full((height, width, 3), color, dtype=numpy.uint8)


def pixmap(color="#00cc00", width=24, height=16):
    result = QPixmap(width, height)
    result.fill(QColor(color))
    return result


def test_incremental_writer_flushes_frame_before_stop_and_qt_reads_timing(tmp_path):
    target = tmp_path / "record.gif"
    writer = gif_writer.IncrementalGifWriter(target)
    writer.append(pixels((255, 0, 0)), timestamp=10.0)
    live = writer.temp_path.read_bytes()
    assert b"\x21\xf9\x04" in live and len(live) > 800
    assert not target.exists()
    writer.append(pixels((0, 204, 0)), timestamp=10.35)
    writer.append(pixels((0, 0, 255)), timestamp=10.5)
    assert writer.finish(timestamp=10.7) == str(target)
    assert not writer.temp_path.exists()
    movie = QMovie(str(target))
    assert movie.isValid() and movie.frameCount() == 3
    colors, delays = [], []
    reader = QImageReader(str(target))
    for index in range(3):
        assert movie.jumpToFrame(index)
        image = movie.currentImage()
        assert (image.width(), image.height()) == (24, 16)
        colors.append(image.pixelColor(3, 3).name())
        assert not reader.read().isNull()
        delays.append(reader.nextImageDelay())
    assert colors == ["#ff0000", "#00cc00", "#0000ff"]
    assert delays == [350, 150, 200]


@pytest.mark.parametrize("finish", [False, True])
def test_empty_or_cancelled_writer_preserves_existing_target(tmp_path, finish):
    target = tmp_path / "record.gif"
    target.write_bytes(b"original")
    writer = gif_writer.IncrementalGifWriter(target)
    if finish:
        assert writer.finish() is None
    else:
        writer.append(pixels((255, 0, 0)))
        writer.cancel()
    assert target.read_bytes() == b"original"
    assert not writer.temp_path.exists()


def test_failed_atomic_replace_preserves_target_and_removes_temporary(tmp_path, monkeypatch):
    target = tmp_path / "record.gif"
    target.write_bytes(b"original")
    writer = gif_writer.IncrementalGifWriter(target)
    writer.append(pixels((255, 0, 0)))
    def denied(*_args):
        raise OSError("replace denied")
    monkeypatch.setattr(gif_writer.os, "replace", denied)
    with pytest.raises(OSError, match="replace denied"):
        writer.finish()
    assert target.read_bytes() == b"original"
    assert not writer.temp_path.exists()


def test_async_queue_rejects_frames_at_count_and_byte_limits(tmp_path):
    entered, release = threading.Event(), threading.Event()
    class SlowWriter(gif_writer.IncrementalGifWriter):
        def append(self, *args, **kwargs):
            entered.set()
            assert release.wait(5)
            return super().append(*args, **kwargs)
    writer = gif_writer.AsyncGifWriter(tmp_path / "slow.gif", writer_factory=SlowWriter,
                                       max_frames=3, max_bytes=36)
    try:
        assert writer.submit(pixels((0, 0, 0), 2, 2), 0.0)
        assert entered.wait(5)
        for stamp in (0.1, 0.2, 0.3):
            assert writer.submit(pixels((255, 0, 0), 2, 2), stamp)
        assert not writer.submit(pixels((0, 0, 255), 2, 2), 0.4)
        assert writer.queued_frames == 3 and writer.queued_bytes == 36
        assert not writer.submit(pixels((0, 0, 255), 4, 4), 0.5)
        start = time.monotonic()
        writer.cancel()
        assert time.monotonic() - start < 0.1
        assert writer.queued_frames == 0 and writer.queued_bytes == 0
    finally:
        release.set()
        wait_until(lambda: writer.done)
    assert not (tmp_path / "slow.gif").exists()


def test_recorder_streams_camera_and_reports_result_after_async_stop(tmp_path):
    recorder = FrameRecorder()
    target = tmp_path / "camera.gif"
    recorder.set_grabber(lambda _rect: pixmap("#000000", 80, 60))
    recorder.set_inset_provider(lambda: pixmap("#ffffff", 20, 20))
    results = []
    recorder.completed.connect(results.append)
    assert recorder.start(QRect(0, 0, 80, 60), target, fps=5)
    assert recorder.frame_count == 1
    recorder.stop()
    recorder.stop()
    wait_until(lambda: bool(results))
    assert results == [str(target)] and recorder.result_path == str(target)
    movie = QMovie(str(target))
    assert movie.jumpToFrame(0)
    assert movie.currentImage().pixelColor(55, 35).name() == "#ffffff"
    assert movie.currentImage().pixelColor(5, 5).name() == "#000000"


def test_recorder_refuses_oversized_region_before_grabbing(tmp_path):
    recorder = FrameRecorder()
    failures = []
    recorder.failed.connect(failures.append)
    recorder.set_grabber(lambda _rect: pytest.fail("oversized capture must not run"))
    assert not recorder.start(QRect(0, 0, 10000, 10000), tmp_path / "huge.gif")
    assert failures and not recorder.running


def test_recorder_reports_writer_failure_without_replacing_target(tmp_path):
    class BrokenWriter(gif_writer.IncrementalGifWriter):
        def append(self, *args, **kwargs):
            raise OSError("disk full")
    target = tmp_path / "failure.gif"
    target.write_bytes(b"original")
    recorder = FrameRecorder(writer_factory=BrokenWriter)
    recorder.set_grabber(lambda _rect: pixmap())
    failures, successes = [], []
    recorder.failed.connect(failures.append)
    recorder.completed.connect(successes.append)
    assert recorder.start(QRect(0, 0, 24, 16), target)
    wait_until(lambda: bool(failures))
    assert "disk full" in failures[0] and not recorder.running
    assert not successes and target.read_bytes() == b"original"
    assert not list(tmp_path.glob("*.part"))


def test_tools_cancel_target_does_not_start_capture(tmp_path, monkeypatch):
    from frontengine.ui.page.tools.tools_setting_ui import ToolsSettingUI
    from PySide6.QtWidgets import QFileDialog
    page = ToolsSettingUI()
    page.recorder.set_grabber(lambda _rect: pytest.fail("cancelled capture must not run"))
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *_args: ("", ""))
    try:
        assert not page.begin_recording(QRect(0, 0, 24, 16))
        assert not page.recorder.running
    finally:
        page.recorder.close()
        page.close()


def test_tools_auto_stop_restores_button_and_allows_next_recording(tmp_path, monkeypatch):
    from frontengine.ui.page.tools.tools_setting_ui import ToolsSettingUI
    from PySide6.QtWidgets import QFileDialog
    page = ToolsSettingUI()
    target = tmp_path / "ui.gif"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *_args: (str(target), ""))
    page.recorder.set_grabber(lambda _rect: pixmap())
    page.record_fps_spinbox.setValue(1)
    page.record_seconds_spinbox.setValue(1)
    try:
        assert page.begin_recording(QRect(0, 0, 24, 16))
        wait_until(lambda: page.last_recording == str(target))
        assert page.record_button.isEnabled()
        assert page.begin_recording(QRect(0, 0, 24, 16))
        wait_until(lambda: not page.recorder.busy)
    finally:
        page.recorder.close()
        page.close()


def test_byte_limit_rejects_frame_even_with_free_queue_slots(tmp_path):
    entered, release = threading.Event(), threading.Event()
    class SlowWriter(gif_writer.IncrementalGifWriter):
        def append(self, *args, **kwargs):
            entered.set()
            assert release.wait(5)
            return super().append(*args, **kwargs)
    writer = gif_writer.AsyncGifWriter(tmp_path / "bytes.gif", writer_factory=SlowWriter,
                                       max_frames=3, max_bytes=36)
    try:
        assert writer.submit(pixels((0, 0, 0), 2, 2), 0.0)
        assert entered.wait(5)
        assert writer.submit(pixels((255, 0, 0), 3, 3), 0.1)
        assert writer.queued_frames == 1 and writer.queued_bytes == 27
        assert not writer.submit(pixels((255, 0, 0), 2, 2), 0.2)
    finally:
        writer.cancel()
        release.set()
        wait_until(lambda: writer.done)


def test_close_during_disk_flush_never_blocks_gui_or_publishes_cancelled_clip(
        tmp_path, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    def slow_sync(_descriptor):
        entered.set()
        assert release.wait(5)
    monkeypatch.setattr(gif_writer.os, "fsync", slow_sync)
    target = tmp_path / "closing.gif"
    target.write_bytes(b"original")
    recorder = FrameRecorder()
    recorder.set_grabber(lambda _rect: pixmap())
    assert recorder.start(QRect(0, 0, 24, 16), target)
    recorder.stop()
    assert entered.wait(5)
    try:
        start = time.monotonic()
        recorder.close()
        assert time.monotonic() - start < 0.1
    finally:
        release.set()
        wait_until(lambda: not recorder.busy)
    assert target.read_bytes() == b"original" and recorder.result_path is None
    assert not list(tmp_path.glob("*.part"))


def test_recorder_drop_timing_keeps_elapsed_playback_and_skips_grab_when_full(tmp_path):
    entered, release = threading.Event(), threading.Event()
    class SlowWriter(gif_writer.IncrementalGifWriter):
        def append(self, *args, **kwargs):
            entered.set()
            assert release.wait(5)
            return super().append(*args, **kwargs)
    now = [0.0]
    recorder = FrameRecorder(writer_factory=SlowWriter, clock=lambda: now[0])
    captures = []
    def grab(_rect):
        captures.append(now[0])
        return pixmap()
    recorder.set_grabber(grab)
    target = tmp_path / "dropped.gif"
    assert recorder.start(QRect(0, 0, 24, 16), target, fps=10, max_seconds=2)
    assert entered.wait(5)
    try:
        for stamp in (0.1, 0.2, 0.3, 0.4, 0.5):
            now[0] = stamp
            recorder.capture_frame()
        assert recorder.frame_count == 4 and recorder.dropped_frames == 2
        assert captures == [0.0, 0.1, 0.2, 0.3]
        assert recorder.queued_frames == 3
        now[0] = 0.6
        recorder.stop()
    finally:
        release.set()
        wait_until(lambda: not recorder.busy)
    reader = QImageReader(str(target))
    delays = []
    for _index in range(4):
        assert not reader.read().isNull()
        delays.append(reader.nextImageDelay())
    assert delays == [100, 100, 100, 300]


def test_long_sequence_is_streamed_without_retaining_rgb_arrays(tmp_path):
    writer = gif_writer.AsyncGifWriter(tmp_path / "long.gif")
    frame = pixels((255, 0, 0))
    for index in range(150):
        wait_until(lambda: writer.can_accept(frame.nbytes))
        assert writer.submit(frame.copy(), index / 10)
        assert writer.queued_frames <= 3 and writer.queued_bytes <= 3456
    writer.stop(15.0)
    wait_until(lambda: writer.done)
    movie = QMovie(writer.result)
    assert movie.isValid() and movie.frameCount() == 150
    assert writer.queued_frames == 0 and writer.queued_bytes == 0


def test_duration_stops_even_when_every_capture_fails(tmp_path):
    now = [0.0]
    recorder = FrameRecorder(clock=lambda: now[0])
    recorder.set_grabber(lambda _rect: None)
    assert recorder.start(QRect(0, 0, 24, 16), tmp_path / "empty.gif", max_seconds=1)
    now[0] = 1.1
    assert not recorder.capture_frame()
    assert not recorder.running and recorder.frame_count == 0
    wait_until(lambda: not recorder.busy)


def test_deleted_qobject_cancels_pending_worker(tmp_path):
    from PySide6.QtCore import QCoreApplication, QEvent
    entered, release = threading.Event(), threading.Event()
    class SlowWriter(gif_writer.IncrementalGifWriter):
        def append(self, *args, **kwargs):
            entered.set()
            assert release.wait(5)
            return super().append(*args, **kwargs)
    target = tmp_path / "deleted.gif"
    recorder = FrameRecorder(writer_factory=SlowWriter)
    recorder.set_grabber(lambda _rect: pixmap())
    recorder.start(QRect(0, 0, 24, 16), target)
    assert entered.wait(5)
    worker = recorder._writer
    recorder.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    release.set()
    wait_until(lambda: worker.done)
    assert not target.exists() and not list(tmp_path.glob("*.part"))


def test_completed_recordings_release_old_writer_connections(tmp_path):
    import gc
    import weakref
    recorder = FrameRecorder()
    recorder.set_grabber(lambda _rect: pixmap())
    assert recorder.start(QRect(0, 0, 24, 16), tmp_path / "released.gif")
    previous = weakref.ref(recorder._writer)
    recorder.stop()
    wait_until(lambda: not recorder.busy)
    gc.collect()
    assert previous() is None


def test_tools_shows_writer_error_and_can_record_again(tmp_path, monkeypatch):
    from frontengine.ui.page.tools.tools_setting_ui import ToolsSettingUI
    from PySide6.QtWidgets import QFileDialog
    class BrokenWriter(gif_writer.IncrementalGifWriter):
        def append(self, *args, **kwargs):
            raise OSError("disk full")
    page = ToolsSettingUI()
    page.recorder._writer_factory = BrokenWriter
    page.recorder.set_grabber(lambda _rect: pixmap())
    target = tmp_path / "failure.gif"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *_args: (str(target), ""))
    try:
        assert page.begin_recording(QRect(0, 0, 24, 16))
        wait_until(lambda: not page.recorder.busy)
        assert "disk full" in page.record_status.text()
        assert page.record_button.isEnabled() and page.last_recording is None
        page.recorder._writer_factory = gif_writer.IncrementalGifWriter
        assert page.begin_recording(QRect(0, 0, 24, 16))
        page.finish_recording()
        wait_until(lambda: not page.recorder.busy)
        assert page.last_recording == str(target)
    finally:
        page.recorder.close()
        page.close()


def test_actual_capture_larger_than_limit_reports_failure_without_success(tmp_path):
    # A capture source can report a larger physical frame than the logical region.
    class OversizedPixmap:
        def isNull(self):
            return False
        def width(self):
            return 5000
        def height(self):
            return 5000
    recorder = FrameRecorder()
    recorder.set_grabber(lambda _rect: OversizedPixmap())
    failures, successes = [], []
    recorder.failed.connect(failures.append)
    recorder.completed.connect(successes.append)
    recorder.start(QRect(0, 0, 24, 16), tmp_path / "huge.gif")
    wait_until(lambda: not recorder.busy)
    assert len(failures) == 1 and "64 MiB" in failures[0]
    assert not successes and not (tmp_path / "huge.gif").exists()
