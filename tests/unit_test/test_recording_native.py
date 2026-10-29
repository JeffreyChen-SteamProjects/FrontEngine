from PySide6.QtCore import QObject, QRect, Signal

from frontengine.utils.recording.frame_recorder import FrameRecorder


class NativeCapture(QObject):
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.started = []
        self.stopped = False

    def start(self, region):
        self.started.append(region)
        return True

    def latest_frame(self, region):
        return None

    def stop(self):
        self.stopped = True


def test_recording_routes_native_source_and_stops_it(tmp_path):
    source = NativeCapture()
    recorder = FrameRecorder(native_capture_factory=lambda parent: source)
    region = QRect(5, 6, 64, 32)
    assert recorder.start(region, tmp_path / 'native.gif')
    assert source.started == [region]
    recorder.stop()
    assert source.stopped
    recorder.close()


def test_rejected_native_start_does_not_create_writer(tmp_path):
    source = NativeCapture()
    source.start = lambda region: False
    recorder = FrameRecorder(native_capture_factory=lambda parent: source)
    assert not recorder.start(QRect(0, 0, 64, 32), tmp_path / 'native.gif')
    assert not recorder.busy
    assert not (tmp_path / 'native.gif').exists()
