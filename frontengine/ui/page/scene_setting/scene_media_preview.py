"""Explicit, muted and bounded live sources retained across editor geometry edits."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage

from frontengine.show.scene.media_frame import SceneMediaFrame

MEDIA_KINDS = ('VIDEO', 'WEB', 'PUPPET', 'SOUND')
SOURCE_FIELDS = ('type', 'file_path', 'url', 'parameters', 'motion', 'expression', 'volume', 'play_rate')


class SceneMediaPreview(QObject):
    """Retain at most eight renderer sources; never auto-start external media on import."""

    changed = Signal(str)
    failed = Signal(str)

    def __init__(self, editor, *, factory=SceneMediaFrame) -> None:
        super().__init__(editor)
        self.editor, self.factory = editor, factory
        self.sources = {}
        self.entries = {}
        self.errors = {}
        self.enabled = False
        self.closed = False

    def sync(self, entries: dict) -> None:
        """Geometry edits reuse sources; removed/replaced resources close immediately."""
        self.entries = {key: entry for key, entry in entries.items() if entry.get('type') in MEDIA_KINDS}
        for key, source in tuple(self.sources.items()):
            entry = self.entries.get(key)
            if entry is None or any(source.entry.get(field) != entry.get(field) for field in SOURCE_FIELDS):
                source.close()
                source.deleteLater()
                del self.sources[key]
        self.errors = {key: error for key, error in self.errors.items() if key in self.entries}
        if self.enabled and self.editor.isVisible():
            self._start_sources()

    def _start_sources(self) -> None:
        for index, (key, entry) in enumerate(self.entries.items()):
            if index >= 8:
                self._failed(key, 'At most eight live media previews can run together')
                continue
            if key not in self.sources:
                try:
                    size = entry.get('size', (320, 480)) if entry.get('type') == 'PUPPET' else (320, 180)
                    width, height = entry.get('width', size[0]), entry.get('height', size[1])
                    factor = min(1, 640 / max(width, height))
                    source = self.factory({**entry, 'width': max(16, int(width * factor)),
                                           'height': max(16, int(height * factor))}, preview=True)
                except (OSError, ValueError, RuntimeError) as error:
                    self._failed(key, str(error))
                    continue
                source.setParent(self.editor)
                source.frame_changed.connect(lambda layer=key: self.changed.emit(layer))
                source.failed.connect(lambda error, layer=key: self._failed(layer, error))
                self.sources[key] = source
                self.errors.pop(key, None)
            self.sources[key].set_active(entry.get('visible', True))

    def _failed(self, key: str, error: str) -> None:
        self.errors[key] = error
        self.failed.emit(key + ': ' + error)
        self.changed.emit(key)

    def image(self, key: str) -> QImage | None:
        """Return the latest provider frame without desktop capture or extra decode."""
        source = self.sources.get(key)
        if source is None or source.closed:
            return None
        if source.frame.isNull() and source.entry.get('type') != 'SOUND':
            return None
        return source.output_frame()

    def set_enabled(self, enabled: bool) -> None:
        """Enabling requires user intent; disabling closes renderers and cached frames."""
        if self.closed:
            return
        self.enabled = enabled
        if enabled and self.editor.isVisible():
            self._start_sources()
        elif not enabled:
            self._clear()
        else:
            self.suspend()

    def suspend(self) -> None:
        """Pause media, JS and native puppet timers while the editor is hidden."""
        for source in self.sources.values():
            source.set_active(False)

    def resume(self) -> None:
        """Resume the enabled sources when the editor becomes visible."""
        if self.enabled and not self.closed:
            self._start_sources()

    def interact(self, key: str) -> None:
        """Open web/puppet input on the selected preview's own renderer."""
        source = self.sources.get(key)
        if source is not None:
            source.interact()

    def audition(self, key: str) -> None:
        """Unmute only the explicitly selected audio/video preview."""
        source = self.sources.get(key)
        if source is not None:
            source.set_muted(False)

    def _clear(self) -> None:
        for source in self.sources.values():
            source.close()
            source.deleteLater()
        self.sources.clear()
        self.errors.clear()

    def shutdown(self) -> None:
        self.closed = True
        self.enabled = False
        self._clear()
