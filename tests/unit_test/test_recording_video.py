"""AVI atomic output, elapsed recording time and GUI pause/cancel controls."""
import struct
import threading
import time

import numpy
import pytest
from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QImage, QImageReader, QPixmap
from PySide6.QtWidgets import QApplication, QFileDialog

from frontengine.utils.recording import avi_writer
from frontengine.utils.recording.frame_recorder import FrameRecorder, frame_budget
from frontengine.utils.recording.gif_writer import AsyncGifWriter


def pixels(color):
    return numpy.full((16, 24, 3), color, numpy.uint8)


def wait(predicate):
    deadline = time.monotonic() + 5
    while not predicate() and time.monotonic() < deadline:
        QApplication.processEvents()
        threading.Event().wait(.005)
    assert predicate()


def test_avi_streams_jpeg_frames_with_disk_index_and_effective_timing(tmp_path):
    target = tmp_path / 'clip.avi'
    writer = avi_writer.IncrementalAviWriter(target, delay_ms=100)
    writer.append(pixels((255, 0, 0)), 10)
    assert writer.temp_path.stat().st_size > 200 and not target.exists()
    writer.append(pixels((0, 0, 255)), 10.3)
    assert writer.finish(10.5) == str(target)
    data = target.read_bytes()
    assert data[:4] == b'RIFF' and data[8:12] == b'AVI '
    assert struct.unpack_from('<I', data, 4)[0] == len(data) - 8
    avih = data.index(b'avih')
    assert struct.unpack_from('<I', data, avih + 24)[0] == 5
    index = data.index(b'idx1')
    assert struct.unpack_from('<I', data, index + 4)[0] == 5 * 16
    colors = []
    movi = data.index(b'movi')
    for entry in range(5):
        _, flags, offset, length = struct.unpack_from('<4sIII', data, index + 8 + entry * 16)
        assert flags == 0x10 and data[movi + offset:movi + offset + 4] == b'00dc'
        image = QImage.fromData(data[movi + offset + 8:movi + offset + 8 + length], 'JPG')
        assert not image.isNull() and image.size().width() == 24
        colors.append(image.pixelColor(2, 2))
    assert all(color.red() > 240 for color in colors[:3])
    assert all(color.blue() > 240 for color in colors[3:])
    assert not list(tmp_path.glob('*.part'))


def test_long_clip_retains_only_one_encoded_frame_and_disk_index(tmp_path):
    writer = avi_writer.IncrementalAviWriter(tmp_path / 'lesson.avi', delay_ms=1000)
    writer.append(pixels((255, 0, 0)), 0)
    writer.append(pixels((0, 255, 0)), 1800)
    assert writer.frame_count == 1801
    assert len(writer._last_jpeg) < 4096
    assert writer._index.tell() == writer.frame_count * 16
    writer.cancel()
    assert not writer.temp_path.exists()
    assert frame_budget(20, 3600, video=True) == 72000


@pytest.mark.parametrize('failure', ['size', 'backward', 'limit', 'encode'])
def test_avi_failure_never_changes_existing_target(tmp_path, monkeypatch, failure):
    target = tmp_path / 'existing.avi'
    target.write_bytes(b'original')
    writer = avi_writer.IncrementalAviWriter(target)
    writer.append(pixels((0, 0, 0)), 1)
    if failure == 'limit':
        monkeypatch.setattr(avi_writer, 'MAX_AVI_BYTES', 10)
    elif failure == 'encode':
        monkeypatch.setattr(avi_writer, '_jpeg', lambda _pixels: (_ for _ in ()).throw(ValueError('encoder unavailable')))
    frame = numpy.zeros((2, 2, 3), numpy.uint8) if failure == 'size' else pixels((1, 1, 1))
    with pytest.raises(ValueError):
        writer.append(frame, 0 if failure == 'backward' else 2)
    writer.cancel()
    assert target.read_bytes() == b'original' and not writer.temp_path.exists()


def test_avi_cancel_during_final_flush_preserves_original_and_does_not_block(tmp_path, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    def sync(_descriptor):
        entered.set()
        assert release.wait(5)
    monkeypatch.setattr(avi_writer.os, 'fsync', sync)
    target = tmp_path / 'existing.avi'
    target.write_bytes(b'original')
    writer = AsyncGifWriter(target, writer_factory=avi_writer.IncrementalAviWriter)
    assert writer.submit(pixels((255, 0, 0)), 0)
    writer.stop(.2)
    assert entered.wait(5)
    try:
        before = time.monotonic()
        writer.cancel()
        assert time.monotonic() - before < .1
    finally:
        release.set()
        wait(lambda: writer.done)
    assert writer.result is None and target.read_bytes() == b'original'
    assert not list(tmp_path.glob('*.part'))


def test_pause_resume_excludes_wall_time_from_gif_and_can_stop_while_paused(tmp_path):
    now = [0.0]
    recorder = FrameRecorder(clock=lambda: now[0])
    pixmap = QPixmap(24, 16)
    pixmap.fill(QColor('red'))
    recorder.set_grabber(lambda _rect: pixmap)
    target = tmp_path / 'paused.gif'
    assert recorder.start(QRect(0, 0, 24, 16), target, fps=10)
    now[0] = .1
    assert recorder.pause() and not recorder.running and recorder.busy
    now[0] = 1000.1
    assert not recorder.capture_frame() and recorder.elapsed_seconds == .1
    assert recorder.resume()
    now[0] = 1000.3
    assert recorder.pause()
    now[0] = 3000
    recorder.stop()
    wait(lambda: not recorder.busy)
    assert recorder.state == 'idle' and recorder.elapsed_seconds == pytest.approx(.3)
    reader = QImageReader(str(target))
    delays = []
    while not reader.read().isNull():
        delays.append(reader.nextImageDelay())
    assert sum(delays) == 300
    recorder.close()


def test_recording_ui_avi_duration_pause_resume_cancel_restores_controls(tmp_path, monkeypatch):
    from frontengine.ui.page.tools.tools_setting_ui import ToolsSettingUI
    page = ToolsSettingUI()
    target = tmp_path / 'ui.avi'
    target.write_bytes(b'original')
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *_args: (str(target), ''))
    pixmap = QPixmap(24, 16)
    pixmap.fill(QColor('red'))
    page.recorder.set_grabber(lambda _rect: pixmap)
    page.record_format.setCurrentIndex(1)
    assert page.record_seconds_spinbox.maximum() == 3600
    try:
        assert page.begin_recording(QRect(0, 0, 24, 16))
        assert page.record_pause.isEnabled() and not page.record_format.isEnabled()
        page.record_pause.click()
        assert page.recorder.state == 'paused' and page.record_button.isEnabled()
        page.record_pause.click()
        assert page.recorder.running
        page.record_cancel.click()
        wait(lambda: not page.recorder.busy)
        assert target.read_bytes() == b'original' and page.record_format.isEnabled()
        assert not page.record_pause.isEnabled() and not page.record_cancel.isEnabled()
    finally:
        page.recorder.close()
        page.close()
