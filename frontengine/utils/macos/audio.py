"""macOS audio adapters. Sample buffers remain in memory and are discarded on close."""
import threading

import numpy as np
from PySide6.QtGui import QGuiApplication

from .backend import get_backend
from .capture import CaptureSession


class MacSystemAudioMeter:
    def __init__(self, device_id=None, session=None) -> None:
        self.session = session or CaptureSession()
        self.last_error = ''
        # ScreenCaptureKit captures the system mix, not an output endpoint.
        if device_id is not None:
            self.last_error = 'ScreenCaptureKit does not select output audio devices'
        else:
            self.session.start(audio=True)

    def level(self):
        samples = self.session.samples()
        return min(1.0, float(np.max(np.abs(samples)))) if samples.size else None

    def close(self) -> None:
        self.session.stop()


class MacMicrophoneMeter:
    def __init__(self, device_id=None, backend=None) -> None:
        self.backend = backend or get_backend()
        self.engine = None
        self._peak = None
        self._lock = threading.Lock()
        self.last_error = ''
        self._tap_installed = False
        application = QGuiApplication.instance()
        if application is not None:
            application.aboutToQuit.connect(self.close)
        state = self.backend.capability('microphone')
        if not state.available:
            self.last_error = state.reason
            return
        if device_id not in (None, 'default'):
            self.last_error = 'AVAudioEngine microphone adapter uses the default input device'
            return
        try:
            av = self.backend.framework('AVFoundation')
            self.engine = av.AVAudioEngine.alloc().init()
            node = self.engine.inputNode()
            fmt = node.outputFormatForBus_(0)
            if fmt.channelCount() == 0:
                raise OSError('No microphone input is available')
            node.installTapOnBus_bufferSize_format_block_(0, 1024, fmt, self._receive)
            self._tap_installed = True
            ok, error = self.engine.startAndReturnError_(None)
            if not ok:
                raise OSError(str(error))
        except Exception as error:
            self.last_error = str(error)
            self.close()

    def _receive(self, buffer, timestamp) -> None:
        channels = buffer.floatChannelData()
        if channels is None:
            return
        stride = max(1, int(buffer.stride()))
        data = np.asarray([channels[0][index * stride] for index in range(buffer.frameLength())],
                          dtype=np.float32)
        with self._lock:
            self._peak = min(1.0, float(np.max(np.abs(data)))) if data.size else 0.0

    def level(self):
        with self._lock:
            return self._peak

    def close(self) -> None:
        engine, self.engine = self.engine, None
        if engine is not None:
            if self._tap_installed:
                engine.inputNode().removeTapOnBus_(0)
                self._tap_installed = False
            engine.stop()
        with self._lock:
            self._peak = None


class MacAudioLevelProvider:
    """One overlay owns this lazy callable and closes it when disabling audio reaction."""

    def __init__(self, microphone: bool = False, factory=None) -> None:
        self._factory = factory or (MacMicrophoneMeter if microphone else MacSystemAudioMeter)
        self._meter = None

    def __call__(self):
        if self._meter is None:
            self._meter = self._factory()
        return self._meter.level()

    def close(self) -> None:
        meter, self._meter = self._meter, None
        if meter is not None:
            meter.close()
