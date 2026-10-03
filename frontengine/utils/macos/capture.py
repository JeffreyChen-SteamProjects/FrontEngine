"""ScreenCaptureKit capture, asynchronous startup and bounded latest-frame delivery."""
import threading

import numpy as np
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage, QGuiApplication

from .backend import get_backend


class CaptureSession(QObject):
    started = Signal()
    failed = Signal(str)

    def __init__(self, parent=None, driver=None) -> None:
        super().__init__(parent)
        self.driver = driver or ScreenCaptureDriver()
        self.running = False
        self.starting = False
        self.last_error = ''
        self._generation = 0
        self._lock = threading.Lock()
        self._frame = QImage()
        self._audio = np.zeros(0, dtype=np.float32)
        driver_handle = self.driver
        self.destroyed.connect(lambda *_args: driver_handle.stop())
        application = QGuiApplication.instance()
        if application is not None:
            application.aboutToQuit.connect(self.stop)

    def start(self, audio: bool = False, window_id=None, display_id=None, region_rect=None) -> bool:
        if self.running or self.starting:
            return True
        self._generation += 1
        generation = self._generation
        self.starting = True

        def completed(error):
            if generation != self._generation:
                self.driver.stop()
                return
            self.starting = False
            self.running = not bool(error)
            if error:
                self.last_error = str(error)
                self.driver.stop()
                self.failed.emit(self.last_error)
            else:
                self.started.emit()

        try:
            self.driver.start(audio=audio, window_id=window_id, display_id=display_id,
                              region_rect=region_rect,
                              started=completed, frame=self._set_frame, samples=self._set_audio,
                              failed=lambda error: self._stream_failed(generation, error))
        except Exception as error:
            completed(str(error))
        return self.starting or self.running

    def _stream_failed(self, generation, error) -> None:
        if generation != self._generation:
            return
        self.running = self.starting = False
        self.last_error = str(error)
        self.failed.emit(self.last_error)

    def _set_frame(self, image) -> None:
        with self._lock:
            self._frame = image.copy()

    def _set_audio(self, samples) -> None:
        with self._lock:
            self._audio = np.asarray(samples, dtype=np.float32).ravel()[-8192:].copy()

    def output_frame(self) -> QImage:
        with self._lock:
            return self._frame.copy()

    def samples(self):
        with self._lock:
            return self._audio.copy()

    def stop(self) -> None:
        self._generation += 1
        self.running = self.starting = False
        self.driver.stop()
        with self._lock:
            self._frame = QImage()
            self._audio = np.zeros(0, dtype=np.float32)


_output_class = None


def _make_output(owner):
    global _output_class
    if _output_class is None:
        import objc
        from Foundation import NSObject

        class FrontEngineStreamOutput(NSObject, protocols=[objc.protocolNamed('SCStreamOutput'),
                                                         objc.protocolNamed('SCStreamDelegate')]):
            def stream_didOutputSampleBuffer_ofType_(self, stream, sample, kind):
                if self.generation != self.owner._generation:
                    return
                try:
                    self.owner.receive(sample, kind)
                except Exception as error:
                    self.owner.options['failed'](str(error))

            def stream_didStopWithError_(self, stream, error):
                if self.generation == self.owner._generation:
                    self.owner.options['failed'](str(error))

        _output_class = FrontEngineStreamOutput
    output = _output_class.alloc().init()
    output.owner = owner
    output.generation = owner._generation
    return output


class ScreenCaptureDriver:
    def __init__(self, backend=None) -> None:
        self.backend = backend or get_backend()
        self.stream = None
        self.output = None
        self.options = {}
        self._cancelled = False
        self._generation = 0

    def start(self, **options) -> None:
        self.options = options
        self._cancelled = False
        self._generation += 1
        generation = self._generation
        state = self.backend.capability('screen_capture')
        if not state.available:
            raise OSError(state.reason)
        sc = self.backend.framework('ScreenCaptureKit')
        sc.SCShareableContent.getShareableContentExcludingDesktopWindows_onScreenWindowsOnly_completionHandler_(
            True, True, lambda content, error: self._content_ready(generation, content, error))

    def _content_ready(self, generation, content, error) -> None:
        if self._cancelled or generation != self._generation:
            return
        if error:
            self.options['started'](str(error))
            return
        try:
            self._create_stream(content)
        except Exception as failure:
            self.options['started'](str(failure))

    def _create_stream(self, content) -> None:
        sc = self.backend.framework('ScreenCaptureKit')
        opts = self.options
        capture_rect = opts.get('region_rect')
        if opts['window_id'] is not None:
            window = next(w for w in content.windows() if w.windowID() == opts['window_id'])
            filt = sc.SCContentFilter.alloc().initWithDesktopIndependentWindow_(window)
            output_size = (window.frame().size.width, window.frame().size.height)
        else:
            display = next((d for d in content.displays() if opts['display_id'] in (None, d.displayID())
                            and self._contains(d.frame(), capture_rect)), None)
            if display is None:
                raise OSError('The region must fit within one capturable display')
            filt = sc.SCContentFilter.alloc().initWithDisplay_excludingWindows_(display, [])
            output_size = (display.width(), display.height())
        config = sc.SCStreamConfiguration.alloc().init()
        config.setCapturesAudio_(opts['audio'])
        config.setSampleRate_(48000)
        config.setChannelCount_(1)
        config.setExcludesCurrentProcessAudio_(True)
        config.setQueueDepth_(3)
        # Small screen output is mandatory even for audio-only streams.
        if capture_rect is not None:
            x, y, width, height = capture_rect
            origin = display.frame().origin
            config.setSourceRect_(((x - origin.x, y - origin.y), (width, height)))
            output_size = (width, height)
        elif hasattr(filt, 'pointPixelScale') and hasattr(filt, 'contentRect'):
            rect = filt.contentRect()
            output_size = (rect.size.width * filt.pointPixelScale(), rect.size.height * filt.pointPixelScale())
        config.setWidth_(32 if opts['audio'] else round(output_size[0]))
        config.setHeight_(32 if opts['audio'] else round(output_size[1]))
        config.setPixelFormat_(0x42475241)  # kCVPixelFormatType_32BGRA
        self.output = _make_output(self)
        self.stream = sc.SCStream.alloc().initWithFilter_configuration_delegate_(filt, config, self.output)
        kinds = [sc.SCStreamOutputTypeScreen]
        if opts['audio']:
            kinds.append(sc.SCStreamOutputTypeAudio)
        for kind in kinds:
            ok, error = self.stream.addStreamOutput_type_sampleHandlerQueue_error_(self.output, kind, None, None)
            if not ok:
                raise OSError(str(error))
        generation, stream, output = self._generation, self.stream, self.output

        def completed(error):
            if generation != self._generation:
                stream.stopCaptureWithCompletionHandler_(lambda error, retained=output: None)
            else:
                opts['started'](error)

        stream.startCaptureWithCompletionHandler_(completed)

    @staticmethod
    def _contains(display_rect, region) -> bool:
        if region is None:
            return True
        x, y, width, height = region
        return (x >= display_rect.origin.x and y >= display_rect.origin.y
                and x + width <= display_rect.origin.x + display_rect.size.width
                and y + height <= display_rect.origin.y + display_rect.size.height)

    def receive(self, sample, kind) -> None:
        if self._cancelled:
            return
        cm = self.backend.framework('CoreMedia')
        sc = self.backend.framework('ScreenCaptureKit')
        if kind == sc.SCStreamOutputTypeAudio:
            self.options['samples'](self._audio_data(sample, cm))
            return
        cv = self.backend.framework('Quartz')
        buffer = cm.CMSampleBufferGetImageBuffer(sample)
        if buffer is None:
            return
        cv.CVPixelBufferLockBaseAddress(buffer, cv.kCVPixelBufferLock_ReadOnly)
        try:
            width, height = cv.CVPixelBufferGetWidth(buffer), cv.CVPixelBufferGetHeight(buffer)
            stride = cv.CVPixelBufferGetBytesPerRow(buffer)
            raw = cv.CVPixelBufferGetBaseAddress(buffer).as_buffer(stride * height)
            self.options['frame'](QImage(raw, width, height, stride, QImage.Format.Format_ARGB32_Premultiplied).copy())
        finally:
            cv.CVPixelBufferUnlockBaseAddress(buffer, cv.kCVPixelBufferLock_ReadOnly)

    @staticmethod
    def _audio_data(sample, cm):
        block = cm.CMSampleBufferGetDataBuffer(sample)
        if block is None:
            return np.zeros(0, dtype=np.float32)
        description = cm.CMSampleBufferGetFormatDescription(sample)
        fmt = cm.CMAudioFormatDescriptionGetStreamBasicDescription(description)
        if fmt is not None and not hasattr(fmt, 'mFormatID'):
            fmt = fmt[0]
        if fmt.mFormatID != 0x6C70636D or fmt.mBitsPerChannel != 32 or not fmt.mFormatFlags & 1:
            raise OSError('ScreenCaptureKit audio is not float32 PCM')
        length = cm.CMBlockBufferGetDataLength(block)
        status, raw = cm.CMBlockBufferCopyDataBytes(block, 0, length, None)
        if status:
            raise OSError('Cannot copy ScreenCaptureKit audio samples')
        return np.frombuffer(raw, dtype=np.float32).copy()

    def stop(self) -> None:
        self._cancelled = True
        self._generation += 1
        stream, self.stream = self.stream, None
        output, self.output = self.output, None
        if stream is not None:
            # Keep the delegate alive until native stop completes.
            stream.stopCaptureWithCompletionHandler_(lambda error, retained=output: None)
