"""Bounded monitor profiles; all movement stays in Qt logical coordinates."""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from pathlib import Path

from PySide6.QtCore import QObject, QRect, QSaveFile, QIODevice, QTimer, Signal, QEvent
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget

MAX_BYTES = 512 * 1024


def current_screens() -> list[dict]:
    """Read stable hardware identity and logical Qt work areas, without Win32 conversion."""
    result = []
    for screen in QGuiApplication.screens():
        name = '\0'.join((screen.name(), screen.manufacturer(), screen.model(), screen.serialNumber()))
        identity = hashlib.sha256(name.encode()).hexdigest()[:24]
        result.append({'id': identity, 'work': screen.availableGeometry().getRect(),
                       'primary': screen == QGuiApplication.primaryScreen(), 'screen': screen,
                       'label': screen.name(), 'dpr': screen.devicePixelRatio()})
    return result


def topology_key(screens: list[dict]) -> str:
    """Resolution, DPI and primary changes share a hardware-combination profile."""
    identities = [screen['id'] for screen in screens]
    if not 1 <= len(identities) <= 16 or len(set(identities)) != len(identities):
        raise ValueError('Monitor identity is missing or ambiguous; automatic restoration is unavailable.')
    return hashlib.sha256('\0'.join(sorted(identities)).encode()).hexdigest()


def overlay_key(widget: QWidget) -> str:
    """Match unique overlay kinds/titles; identical duplicates are deliberately excluded."""
    kind = f'{type(widget).__module__}.{type(widget).__qualname__}'
    return kind + ':' + widget.windowTitle()[:512]


def unique_overlays(provider, excluded=None, *, unique_only: bool = True) -> list[tuple[str, QWidget]]:
    """Deduplicate live registered windows and reject fullscreen/scene/ambiguous entries."""
    windows, seen = [], set()
    for group in provider():
        for widget in group[:]:
            try:
                if id(widget) in seen or not isinstance(widget, QWidget) or not widget.isWindow():
                    continue
                seen.add(id(widget))
                if widget.isFullScreen() or getattr(widget, 'scene', None) is not None:
                    continue
                if excluded and excluded(widget):
                    continue
                windows.append((overlay_key(widget), widget))
            except RuntimeError:
                continue
    counts = Counter(key for key, _ in windows)
    return [(key, widget) for key, widget in windows if not unique_only or counts[key] == 1][:200]


def placement(entry: dict, work: tuple, widget: QWidget) -> QRect:
    """Reconstruct proportionate position and logical size, then keep the entire window visible."""
    x, y, width, height = work
    saved_width, saved_height = entry['size']
    width = max(1, width)
    height = max(1, height)
    w = min(width, max(widget.minimumWidth(), min(widget.maximumWidth(), round(saved_width))))
    h = min(height, max(widget.minimumHeight(), min(widget.maximumHeight(), round(saved_height))))
    px = x + round(entry['anchor'][0] * width)
    py = y + round(entry['anchor'][1] * height)
    return QRect(min(x + width - w, max(x, px)), min(y + height - h, max(y, py)), w, h)


class ProfileRepository:
    """Twenty hardware combinations and two hundred placements each, written atomically."""
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.profiles: dict = {}
        self.loaded = False

    def load(self) -> None:
        if self.loaded:
            return
        if self.path.exists():
            if self.path.is_symlink() or self.path.stat().st_size > MAX_BYTES:
                raise ValueError('Invalid monitor profile file size or path.')
            value = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(value, dict) or value.get('version') != 1:
                raise ValueError('Unsupported monitor profile version.')
            self.profiles = validate_profiles(value.get('profiles'))
        self.loaded = True

    def save(self, key: str, entries: dict) -> None:
        self.load()
        candidate = dict(self.profiles)
        if key not in candidate and len(candidate) >= 20:
            raise ValueError('Monitor profile limit reached (20 combinations).')
        candidate[key] = entries
        candidate = validate_profiles(candidate)
        data = json.dumps({'version': 1, 'profiles': candidate}, ensure_ascii=False).encode('utf-8')
        if len(data) > MAX_BYTES:
            raise ValueError('Monitor profiles exceed 512 KiB.')
        if self.path.is_symlink():
            raise ValueError('Monitor profile destination cannot be a symbolic link.')
        target = QSaveFile(str(self.path))
        if not target.open(QIODevice.OpenModeFlag.WriteOnly):
            raise OSError(target.errorString())
        if target.write(data) != len(data) or not target.commit():
            target.cancelWriting()
            raise OSError(target.errorString())
        self.profiles = candidate


def validate_profiles(profiles: object) -> dict:
    """Validate external placement data before touching any live geometry."""
    if not isinstance(profiles, dict) or len(profiles) > 20:
        raise ValueError('Invalid monitor profile count.')
    for key, entries in profiles.items():
        if not isinstance(key, str) or len(key) != 64 or any(c not in '0123456789abcdef' for c in key):
            raise ValueError('Invalid monitor combination identity.')
        if not isinstance(entries, dict) or len(entries) > 200:
            raise ValueError('Invalid monitor placement count.')
        for name, entry in entries.items():
            if not isinstance(name, str) or len(name) > 1024 or not isinstance(entry, dict):
                raise ValueError('Invalid overlay placement.')
            identity = entry.get('screen')
            if not isinstance(identity, str) or not 1 <= len(identity) <= 128:
                raise ValueError('Invalid monitor identity.')
            for field, low, high in (('anchor', -10, 10), ('size', 1, 16384)):
                values = entry.get(field)
                if not isinstance(values, list) or len(values) != 2:
                    raise ValueError('Invalid overlay coordinates.')
                if any(type(v) not in (int, float) or not math.isfinite(v) or not low <= v <= high for v in values):
                    raise ValueError('Invalid overlay coordinate bounds.')
    return profiles


class MonitorProfileService(QObject):
    """Explicit save/restore, default-off automatic adaptation with debounced screen signals."""
    changed = Signal(str)
    failed = Signal(str)

    def __init__(self, path: Path, provider, parent=None, *, screens=current_screens, excluded=None) -> None:
        super().__init__(parent)
        self.repository = ProfileRepository(path)
        self.provider, self.screens, self.excluded = provider, screens, excluded
        self.enabled, self.closed = False, False
        self._connections: list = []
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.adapt)

    def save_current(self) -> int:
        """Save only unique currently registered overlays; never serialize native handles."""
        screens = self.screens()
        key = topology_key(screens)
        entries = {}
        for name, widget in unique_overlays(self.provider, self.excluded):
            rect = widget.geometry()
            screen = max(screens, key=lambda s: rect.intersected(QRect(*s['work'])).width() *
                         rect.intersected(QRect(*s['work'])).height())
            x, y, width, height = screen['work']
            entries[name] = {'screen': screen['id'], 'anchor': [(rect.x() - x) / max(1, width),
                                                              (rect.y() - y) / max(1, height)],
                             'size': [rect.width(), rect.height()]}
        if not entries:
            raise ValueError('No unique movable registered overlays to save.')
        self.repository.save(key, entries)
        self.changed.emit(str(len(entries)))
        return len(entries)

    def restore_current(self) -> int:
        """Restore saved positions, or clamp existing positions if this combination is new."""
        screens = self.screens()
        key = topology_key(screens)
        self.repository.load()
        entries = self.repository.profiles.get(key, {})
        windows = unique_overlays(self.provider, self.excluded, unique_only=False)
        counts = Counter(name for name, _ in windows)
        count = 0
        for name, widget in windows:
            rect = widget.geometry()
            entry = entries.get(name) if counts[name] == 1 else None
            if entry is None:
                entry = {'size': [rect.width(), rect.height()], 'anchor': [0, 0], 'screen': ''}
                screen = max(screens, key=lambda s: int(s.get('primary', False)))
                if any(QRect(*s['work']).contains(rect) for s in screens):
                    continue
                x, y, w, h = screen['work']
                entry['anchor'] = [(rect.x() - x) / max(1, w), (rect.y() - y) / max(1, h)]
            else:
                screen = next((s for s in screens if s['id'] == entry['screen']), None)
                if screen is None:
                    continue
            self._place(widget, screen, placement(entry, screen['work'], widget))
            count += 1
        self.changed.emit(str(count))
        return count

    @staticmethod
    def _place(widget: QWidget, screen: dict, rect: QRect) -> None:
        if screen.get('screen') is not None and widget.screen() != screen['screen']:
            widget.setScreen(screen['screen'])
        if widget.geometry() != rect:
            widget.setGeometry(rect)

    def set_enabled(self, enabled: bool) -> None:
        """Observe Qt topology only after opt-in; never change OS display configuration."""
        self._disconnect()
        application = QGuiApplication.instance()
        application.removeEventFilter(self)
        self.enabled = bool(enabled) and not self.closed
        if not self.enabled:
            self.timer.stop()
            return
        application.installEventFilter(self)
        for signal in (application.screenAdded, application.screenRemoved, application.primaryScreenChanged):
            self._connect(signal, self._topology_changed)
        self._watch_screens()
        self.timer.start()

    def eventFilter(self, watched, event) -> bool:
        if self.enabled and event.type() == QEvent.Type.Show and isinstance(watched, QWidget):
            if any(widget is watched for _, widget in unique_overlays(self.provider, self.excluded)):
                self.timer.start()
        return False

    def _connect(self, signal, callback) -> None:
        signal.connect(callback)
        self._connections.append((signal, callback))

    def _watch_screens(self) -> None:
        for screen in QGuiApplication.screens():
            for signal in (screen.geometryChanged, screen.availableGeometryChanged,
                           screen.logicalDotsPerInchChanged, screen.physicalDotsPerInchChanged):
                self._connect(signal, self._topology_changed)

    def _topology_changed(self, *_args) -> None:
        if self.enabled and not self.closed:
            self.set_enabled(True)
            self.timer.start()

    def adapt(self) -> None:
        """Guard native signal delivery; unsupported/invalid profiles produce a visible reason."""
        if not self.enabled or self.closed:
            return
        try:
            self.restore_current()
        except (ValueError, OSError, RuntimeError) as error:
            self.failed.emit(str(error))

    def _disconnect(self) -> None:
        for signal, callback in self._connections:
            try:
                signal.disconnect(callback)
            except (RuntimeError, TypeError):
                pass
        self._connections.clear()

    def stop(self) -> None:
        """Disconnect removed-screen signals and stop pending adaptation."""
        self.closed = True
        self.set_enabled(False)
