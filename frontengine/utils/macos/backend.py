from dataclasses import dataclass
from importlib import import_module
import platform
import sys


@dataclass(frozen=True)
class Capability:
    supported: bool
    available: bool
    reason: str = ''


class MacOSBackend:
    """Framework boundary with injectable imports and explicit permission state."""

    def __init__(self, loader=import_module) -> None:
        self._loader = loader
        self._frameworks = {}
        self.last_error = ''

    def framework(self, name: str):
        if name not in self._frameworks:
            self._frameworks[name] = self._loader(name)
        return self._frameworks[name]

    def capability(self, name: str) -> Capability:
        if name in ('foreign_opacity', 'foreign_topmost', 'spaces', 'capture_exclusion'):
            return Capability(False, False, 'No supported public API for foreign window control')
        try:
            if name in ('screen_capture', 'system_audio'):
                if self._loader is import_module and sys.platform == 'darwin':
                    version = platform.mac_ver()[0]
                    if version and int(version.split('.')[0]) < 13:
                        return Capability(False, False, 'ScreenCaptureKit integration requires macOS 13+')
                self.framework('ScreenCaptureKit')
                granted = bool(self.framework('Quartz').CGPreflightScreenCaptureAccess())
                return Capability(True, granted, '' if granted else
                                  'Allow Screen Recording in System Settings > Privacy & Security, then restart')
            if name in ('window_move', 'global_hotkey', 'media_keys'):
                q = self.framework('Quartz')
                if name == 'global_hotkey' and hasattr(q, 'CGPreflightListenEventAccess'):
                    if not q.CGPreflightListenEventAccess():
                        return Capability(True, False,
                                          'Allow Input Monitoring in System Settings > Privacy & Security, then restart')
                granted = bool(self.framework('ApplicationServices').AXIsProcessTrusted())
                return Capability(True, granted, '' if granted else
                                  'Allow Accessibility in System Settings > Privacy & Security, then restart')
            if name == 'microphone':
                av = self.framework('AVFoundation')
                granted = av.AVCaptureDevice.authorizationStatusForMediaType_(av.AVMediaTypeAudio) == 3
                return Capability(True, granted, '' if granted else
                                  'Allow Microphone in System Settings > Privacy & Security')
            if name in ('window_geometry', 'midi'):
                self.framework('Quartz' if name == 'window_geometry' else 'CoreMIDI')
                return Capability(True, True)
        except (ImportError, AttributeError, OSError) as error:
            return Capability(False, False, f'Install FrontEngine macos extra on macOS 13+: {error}')
        return Capability(False, False, f'Unknown capability: {name}')

    def _windows(self):
        try:
            q = self.framework('Quartz')
            return [item for item in q.CGWindowListCopyWindowInfo(q.kCGWindowListOptionOnScreenOnly,
                                                                 q.kCGNullWindowID) or []
                    if item.get('kCGWindowLayer') == 0 and item.get('kCGWindowNumber')]
        except (ImportError, AttributeError, OSError) as error:
            self.last_error = str(error)
            return []

    def list_windows(self) -> list[tuple[int, str]]:
        return [(int(w['kCGWindowNumber']), str(w['kCGWindowName'])) for w in self._windows()
                if w.get('kCGWindowName')]

    @staticmethod
    def _rect(window):
        bounds = window.get('kCGWindowBounds', {})
        return tuple(round(bounds.get(key, 0)) for key in ('X', 'Y', 'Width', 'Height'))

    def window_geometry(self, handle: int):
        return next((self._rect(w) for w in self._windows() if w['kCGWindowNumber'] == handle), None)

    def standable_windows(self, exclude_handles=()) -> list[tuple[int, int, int]]:
        return [(x, x + width, y) for w in self._windows()
                if w['kCGWindowNumber'] not in exclude_handles
                for x, y, width, height in [self._rect(w)] if width >= 120 and height >= 80]

    def _ax_window(self, handle):
        ax = self.framework('ApplicationServices')
        window = next((w for w in self._windows() if w['kCGWindowNumber'] == handle), None)
        if window is None:
            return None
        app = ax.AXUIElementCreateApplication(window['kCGWindowOwnerPID'])
        error, candidates = ax.AXUIElementCopyAttributeValue(app, ax.kAXWindowsAttribute, None)
        if error:
            return None
        matches = []
        target = self._rect(window)
        for candidate in candidates or []:
            err, title = ax.AXUIElementCopyAttributeValue(candidate, ax.kAXTitleAttribute, None)
            if err or (window.get('kCGWindowName') and title != window['kCGWindowName']):
                continue
            ep, position = ax.AXUIElementCopyAttributeValue(candidate, ax.kAXPositionAttribute, None)
            es, size = ax.AXUIElementCopyAttributeValue(candidate, ax.kAXSizeAttribute, None)
            if ep or es:
                continue
            okp, point = ax.AXValueGetValue(position, ax.kAXValueCGPointType, None)
            oks, extent = ax.AXValueGetValue(size, ax.kAXValueCGSizeType, None)
            if okp and oks and all(abs(a - b) <= 2 for a, b in
                                   zip(tuple(point) + tuple(extent), target)):
                matches.append(candidate)
        return matches[0] if len(matches) == 1 else None

    def move_window(self, handle: int, x: int, y: int, width: int, height: int) -> bool:
        state = self.capability('window_move')
        if not state.available:
            self.last_error = state.reason
            return False
        try:
            ax = self.framework('ApplicationServices')
            window = self._ax_window(handle)
            if window is None:
                self.last_error = 'Window cannot be uniquely matched to an Accessibility element'
                return False
            position = ax.AXValueCreate(ax.kAXValueCGPointType, (x, y))
            size = ax.AXValueCreate(ax.kAXValueCGSizeType, (max(40, width), max(40, height)))
            return (ax.AXUIElementSetAttributeValue(window, ax.kAXSizeAttribute, size) == 0
                    and ax.AXUIElementSetAttributeValue(window, ax.kAXPositionAttribute, position) == 0)
        except (ImportError, AttributeError, OSError, ValueError) as error:
            self.last_error = str(error)
            return False

    def foreground_window(self):
        try:
            app = self.framework('AppKit').NSWorkspace.sharedWorkspace().frontmostApplication()
            return next((w['kCGWindowNumber'] for w in self._windows()
                         if w.get('kCGWindowOwnerPID') == app.processIdentifier()), None)
        except (ImportError, AttributeError, OSError):
            return None


_backend = None


def get_backend() -> MacOSBackend:
    global _backend
    if _backend is None:
        _backend = MacOSBackend()
    return _backend
