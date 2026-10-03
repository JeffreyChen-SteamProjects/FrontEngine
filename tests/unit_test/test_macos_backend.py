from types import SimpleNamespace


def frameworks(granted=True):
    quartz = SimpleNamespace(CGPreflightScreenCaptureAccess=lambda: granted)
    accessibility = SimpleNamespace(AXIsProcessTrusted=lambda: granted)
    av = SimpleNamespace(AVMediaTypeAudio='audio', AVAuthorizationStatusAuthorized=3,
                         AVCaptureDevice=SimpleNamespace(authorizationStatusForMediaType_=lambda _: 3 if granted else 2))
    return {'Quartz': quartz, 'ScreenCaptureKit': object(), 'AVFoundation': av,
            'CoreMIDI': object(), 'AppKit': object(), 'ApplicationServices': accessibility}


def test_capabilities_distinguish_permission_and_public_api_limitations():
    from frontengine.utils.macos.backend import MacOSBackend
    backend = MacOSBackend(loader=lambda name: frameworks(False)[name])
    assert not backend.capability('screen_capture').available
    assert 'Screen Recording' in backend.capability('system_audio').reason
    assert 'Accessibility' in backend.capability('window_move').reason
    assert 'Microphone' in backend.capability('microphone').reason
    assert not backend.capability('foreign_opacity').supported
    assert not backend.capability('foreign_topmost').supported
    assert not backend.capability('spaces').supported


def test_native_window_listing_filters_shells_and_preserves_points():
    from frontengine.utils.macos.backend import MacOSBackend
    q = frameworks()['Quartz']
    q.kCGWindowListOptionOnScreenOnly = 1
    q.kCGNullWindowID = 0
    q.CGWindowListCopyWindowInfo = lambda *_: [
        {'kCGWindowNumber': 5, 'kCGWindowOwnerPID': 100, 'kCGWindowLayer': 0,
         'kCGWindowName': 'Editor', 'kCGWindowBounds': {'X': -800, 'Y': 20, 'Width': 400, 'Height': 300}},
        {'kCGWindowNumber': 6, 'kCGWindowLayer': 4, 'kCGWindowName': 'Menu'}]
    backend = MacOSBackend(loader=lambda name: q if name == 'Quartz' else frameworks()[name])
    assert backend.list_windows() == [(5, 'Editor')]
    assert backend.window_geometry(5) == (-800, 20, 400, 300)
    assert backend.standable_windows() == [(-800, -400, 20)]


def test_missing_framework_has_actionable_reason():
    from frontengine.utils.macos.backend import MacOSBackend

    def missing(_):
        raise ImportError('not installed')

    assert 'macos' in MacOSBackend(loader=missing).capability('screen_capture').reason


def test_midi_parser_handles_running_status_realtime_and_split_packets():
    from frontengine.utils.macos.midi import MIDIParser
    parser = MIDIParser()
    assert parser.feed(bytes([0xB0, 7])) == []
    assert parser.feed(bytes([0xF8, 64, 8, 65])) == [0x4007B0, 0x4108B0]
    assert parser.feed(bytes([0xF0, 1, 2, 0xF7, 0x90, 36, 127])) == [0x7F2490]


def test_capture_stop_during_start_releases_late_stream():
    from frontengine.utils.macos.capture import CaptureSession
    calls = []

    class Driver:
        def start(self, **options):
            self.options = options

        def stop(self):
            calls.append('stop')

    driver = Driver()
    session = CaptureSession(driver=driver)
    assert session.start(audio=True)
    session.stop()
    driver.options['started'](None)
    assert not session.running
    assert calls == ['stop', 'stop']


def test_capture_failure_is_reported_and_no_success_state():
    from frontengine.utils.macos.capture import CaptureSession

    class Driver:
        def start(self, **options):
            options['started']('permission denied')

        def stop(self):
            pass

    session = CaptureSession(driver=Driver())
    errors = []
    session.failed.connect(errors.append)
    session.start(audio=True)
    assert not session.running
    assert errors == ['permission denied']


def test_darwin_routes_existing_geometry_and_pet_edges(monkeypatch):
    from frontengine.utils.macos import backend
    from frontengine.utils.platform_info import platform_info
    from frontengine.utils.window_pin import window_layout
    fake = SimpleNamespace(window_geometry=lambda handle: (1, 2, 300, 200),
                           standable_windows=lambda excluded: [(1, 301, 2)])
    monkeypatch.setattr(backend, '_backend', fake)
    monkeypatch.setattr(platform_info.sys, 'platform', 'darwin')
    assert platform_info.standable_windows() == [(1, 301, 2)]
    assert window_layout.window_geometry(5) == (1, 2, 300, 200)


def test_region_adapter_starts_native_session_and_delivers_expected_size():
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QColor, QImage
    from frontengine.utils.macos.region_capture import RegionCaptureAdapter

    class Session:
        def start(self, **options):
            self.options = options
            return True

        def stop(self):
            self.stopped = True

        def output_frame(self):
            image = QImage(40, 20, QImage.Format.Format_ARGB32)
            image.fill(QColor('red'))
            return image

    session = Session()
    adapter = RegionCaptureAdapter(session=session)
    assert adapter.start(QRect(-400, 30, 20, 10))
    assert session.options['region_rect'] == (-400, 30, 20, 10)
    assert adapter.latest_frame().size().width() == 20
    assert adapter.latest_frame().toImage().pixelColor(0, 0) == QColor('red')
    adapter.stop()
    assert session.stopped


def test_layout_and_focus_window_routes_are_available_on_mac(monkeypatch):
    from frontengine.utils.macos import backend
    from frontengine.utils.window_pin import window_layout
    from frontengine.show.focus_shield import focus_shield_widget
    state = SimpleNamespace(available=True)
    fake = SimpleNamespace(capability=lambda name: state, foreground_window=lambda: 5,
                           window_geometry=lambda handle: (-400, 30, 20, 10))
    monkeypatch.setattr(backend, '_backend', fake)
    monkeypatch.setattr(window_layout.sys, 'platform', 'darwin')
    assert window_layout.available()
    assert focus_shield_widget.active_window_rect() == (-400, 30, 20, 10)
    widget = focus_shield_widget.DimBackgroundWidget()
    assert widget._to_logical((-400, 30, 20, 10)) == (-400, 30, 20, 10)
    widget.close()


def test_stale_screen_content_callback_does_not_start_a_new_session():
    from frontengine.utils.macos.capture import ScreenCaptureDriver
    callbacks = []
    sc = SimpleNamespace(SCShareableContent=SimpleNamespace(
        getShareableContentExcludingDesktopWindows_onScreenWindowsOnly_completionHandler_=lambda *args: callbacks.append(args[-1])))
    backend = SimpleNamespace(capability=lambda name: SimpleNamespace(available=True),
                              framework=lambda name: sc)
    driver = ScreenCaptureDriver(backend)
    driver.start()
    driver.stop()
    driver.start()
    callbacks[0](None, 'old permission failure')
    assert not driver._cancelled


def test_media_codes_send_down_and_up_but_stop_is_explicitly_unsupported():
    from frontengine.utils.macos.input import send_media_key
    events = []
    appkit = SimpleNamespace(NSSystemDefined=14, NSEvent=SimpleNamespace(
        otherEventWithType_location_modifierFlags_timestamp_windowNumber_context_subtype_data1_data2_=
        lambda *args: SimpleNamespace(CGEvent=lambda: args[-2])))
    quartz = SimpleNamespace(kCGHIDEventTap=0, CGEventPost=lambda tap, event: events.append(event))
    backend = SimpleNamespace(capability=lambda name: SimpleNamespace(available=True, reason=''),
                              framework=lambda name: appkit if name == 'AppKit' else quartz)
    assert send_media_key('media_play_pause', backend)
    assert events == [(16 << 16) | (0xA << 8), (16 << 16) | (0xB << 8)]
    assert not send_media_key('media_stop', backend)


def test_function_virtual_key_maps_to_mac_f12():
    from frontengine.utils.macos.input import key_is_pressed
    quartz = SimpleNamespace(kCGEventSourceStateCombinedSessionState=0,
                             CGEventSourceKeyState=lambda source, code: code == 111)
    assert key_is_pressed(0x7B, SimpleNamespace(framework=lambda name: quartz))


def test_native_one_shot_hides_selection_uses_global_region_and_closes_after_frame(monkeypatch):
    from PySide6.QtCore import QPoint, Signal, QObject
    from PySide6.QtGui import QPixmap, QColor
    from frontengine.show.capture import region_capture

    class Adapter(QObject):
        failed = Signal(str)

        def start(self, region):
            self.region = region
            return True

        def latest_frame(self):
            image = QPixmap(20, 10)
            image.fill(QColor('red'))
            return image

        def stop(self):
            self.stopped = True

    adapter = Adapter()
    results = []
    monkeypatch.setattr(region_capture.sys, 'platform', 'darwin')
    widget = region_capture.RegionCaptureWidget(lambda *args: results.append(args),
                                                native_capture_factory=lambda parent: adapter)
    widget.setGeometry(-400, 30, 100, 100)
    widget.begin(QPoint(10, 20))
    assert widget.finish(QPoint(30, 30)) is None
    widget._start_native_capture()
    assert adapter.region.topLeft() == QPoint(-390, 50)
    assert widget._capture_pending
    widget._poll_native_capture()
    assert results[0][1].topLeft() == QPoint(-390, 50)
    assert results[0][0].size().width() == 20
    assert adapter.stopped
    assert not widget._capture_pending


def test_coremidi_intel_packet_alignment_preserves_second_message(monkeypatch):
    import ctypes
    import struct
    import platform
    from frontengine.utils.macos import midi
    received = []
    source = midi.CoreMIDIInput.__new__(midi.CoreMIDIInput)
    source.parser = midi.MIDIParser()
    source.callback = received.append
    monkeypatch.setattr(platform, 'machine', lambda: 'x86_64')
    packet = lambda raw: struct.pack('<QH', 0, len(raw)) + raw
    raw = struct.pack('<I', 2) + packet(bytes([0xB0, 7, 64])) + packet(bytes([0x90, 36, 127]))
    memory = ctypes.create_string_buffer(raw, 256)
    source._receive(ctypes.addressof(memory), None, None)
    assert received == [0x4007B0, 0x7F2490]


def test_microphone_interleaved_input_respects_channel_stride():
    import threading
    from frontengine.utils.macos.audio import MacMicrophoneMeter
    meter = MacMicrophoneMeter.__new__(MacMicrophoneMeter)
    meter._lock = threading.Lock()
    buffer = SimpleNamespace(floatChannelData=lambda: [[0.1, 0.9, 0.2, 0.9]],
                             frameLength=lambda: 2, stride=lambda: 2)
    meter._receive(buffer, None)
    assert abs(meter.level() - 0.2) < 1e-6


def test_audio_level_provider_opens_lazily_and_releases_capture_on_close():
    from frontengine.utils.macos.audio import MacAudioLevelProvider
    calls = []

    class Meter:
        def __init__(self):
            calls.append('open')

        def level(self):
            return 0.5

        def close(self):
            calls.append('close')

    provider = MacAudioLevelProvider(factory=Meter)
    assert calls == []
    assert provider() == 0.5
    assert provider() == 0.5
    provider.close()
    assert calls == ['open', 'close']


def test_screen_capture_audio_copy_uses_pyobjc_buffer_boundary():
    import numpy as np
    from frontengine.utils.macos.capture import ScreenCaptureDriver
    raw = np.asarray([0.1, 0.5, -0.8], dtype=np.float32).tobytes()
    cm = SimpleNamespace(CMSampleBufferGetDataBuffer=lambda sample: 'block',
                         CMSampleBufferGetFormatDescription=lambda sample: 'description',
                         CMAudioFormatDescriptionGetStreamBasicDescription=lambda desc: SimpleNamespace(
                             mFormatID=0x6C70636D, mBitsPerChannel=32, mFormatFlags=1),
                         CMBlockBufferGetDataLength=lambda block: len(raw),
                         CMBlockBufferCopyDataBytes=lambda block, offset, length, output: (0, raw))
    assert np.allclose(ScreenCaptureDriver._audio_data('sample', cm), [0.1, 0.5, -0.8])


def test_accessibility_window_match_unboxes_tuple_geometry_and_moves_public_element():
    from frontengine.utils.macos.backend import MacOSBackend
    frameworks_map = frameworks()
    quartz = frameworks_map['Quartz']
    quartz.kCGWindowListOptionOnScreenOnly = 1
    quartz.kCGNullWindowID = 0
    quartz.CGWindowListCopyWindowInfo = lambda *_: [
        {'kCGWindowNumber': 5, 'kCGWindowOwnerPID': 100, 'kCGWindowLayer': 0,
         'kCGWindowName': 'Editor', 'kCGWindowBounds': {'X': -800, 'Y': 20, 'Width': 400, 'Height': 300}}]
    ax = frameworks_map['ApplicationServices']
    ax.kAXWindowsAttribute, ax.kAXTitleAttribute = 'windows', 'title'
    ax.kAXPositionAttribute, ax.kAXSizeAttribute = 'position', 'size'
    ax.kAXValueCGPointType, ax.kAXValueCGSizeType = 1, 2
    ax.AXUIElementCreateApplication = lambda pid: 'app'
    values = {'windows': ['editor'], 'title': 'Editor', 'position': (-800, 20), 'size': (400, 300)}
    ax.AXUIElementCopyAttributeValue = lambda element, attr, output: (0, values[attr])
    ax.AXValueGetValue = lambda value, kind, output: (True, value)
    ax.AXValueCreate = lambda kind, value: value
    changes = []
    ax.AXUIElementSetAttributeValue = lambda element, attr, value: changes.append((attr, value)) or 0
    backend = MacOSBackend(loader=lambda name: frameworks_map[name])
    assert backend.move_window(5, -700, 40, 300, 200)
    assert changes == [('size', (300, 200)), ('position', (-700, 40))]


def test_coremidi_native_handles_and_cf_string_are_released(monkeypatch):
    import ctypes
    import sys
    from frontengine.utils.macos.midi import CoreMIDIInput
    monkeypatch.setitem(sys.modules, 'CoreMIDI', SimpleNamespace(
        MIDIGetNumberOfSources=lambda: 1, MIDIGetSource=lambda index: 101))
    calls = []

    def create_client(name, notify, context, output):
        assert name == 1234
        ctypes.cast(output, ctypes.POINTER(ctypes.c_uint32))[0] = 1
        return 0

    def create_port(client, name, callback, context, output):
        assert name == 1234
        ctypes.cast(output, ctypes.POINTER(ctypes.c_uint32))[0] = 2
        return 0

    lib = SimpleNamespace(MIDIClientCreate=create_client, MIDIInputPortCreate=create_port,
        MIDIPortConnectSource=lambda *_: 0, MIDIPortDisconnectSource=lambda *_: calls.append('disconnect'),
        MIDIPortDispose=lambda *_: calls.append('port'), MIDIClientDispose=lambda *_: calls.append('client'))
    foundation = SimpleNamespace(CFStringCreateWithCString=lambda *_: 1234,
                                 CFRelease=lambda value: calls.append(('name', value)))
    source = CoreMIDIInput(lambda message: None, library=lib, foundation=foundation)
    assert source.start(0)
    source.stop()
    source.stop()
    assert calls == [('name', 1234), 'disconnect', 'port', 'client']
