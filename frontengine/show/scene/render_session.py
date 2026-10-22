"""Independent fixed-size scene composition without any desktop capture."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, Qt, QSize, Signal
from PySide6.QtGui import QImage, QImageReader

from frontengine.show.scene.scene import SceneManager
from frontengine.show.scene.compositor_view import SceneCompositorView
from frontengine.utils.scene_format.scene_editor_document import validate_geometry

OUTPUT_SIZES = ((640, 480), (1280, 720), (1920, 1080))


class SceneRenderSession(QObject):
    """Snapshot renderer; callers close it before releasing referenced assets."""

    failed = Signal(str)

    def __init__(self, entries: dict, size: tuple[int, int], parent=None,
                 *, manager_factory: Callable = SceneManager) -> None:
        super().__init__(parent)
        if size not in OUTPUT_SIZES:
            raise ValueError('Choose a supported fixed scene output resolution')
        validated = validate_geometry(entries)
        if not validated or len(validated) > 256:
            raise ValueError('Scene output requires 1–256 supported layers')
        if sum(entry.get('type') in ('VIDEO', 'WEB', 'PUPPET', 'SOUND') for entry in validated.values()) > 8:
            raise ValueError('Scene output supports at most eight native media sources')
        self.size = QSize(*size)
        self.manager = manager_factory()
        self.view = None
        self.closed = False
        try:
            self._validate_images(validated)
            for key, entry in validated.items():
                for field in ('file_path', 'text_file', 'script_path'):
                    if entry.get(field) and not Path(entry[field]).is_file():
                        raise ValueError(f'Missing scene output resource: {entry[field]}')
                self.manager.add_entry(key, entry)
                widget = self.manager.widget_list[-1].widget()
                if hasattr(widget, 'failed'):
                    widget.failed.connect(lambda error, layer=key: self.failed.emit(layer + ': ' + error))
            pixels = sum(proxy.widget().width() * proxy.widget().height() for proxy in self.manager.widget_list)
            if pixels > 16_777_216:
                raise ValueError('Scene output exceeds the 16 megapixel layer raster budget')
            self.view = SceneCompositorView(self.manager.graphic_scene, 'software')
            self.view.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
            self.view.resize(*size)
            self.view.set_muted(True)
            self.view.show()
        except (OSError, ValueError, RuntimeError):
            self.close()
            raise

    def frame(self) -> QImage:
        """Return scene composition at the fixed logical resolution, never a screen grab."""
        if self.closed:
            return QImage()
        frame = self.view.output_frame()
        if frame.size() != self.size:
            frame = frame.scaled(self.size)
        frame.setDevicePixelRatio(1)
        return frame

    def _validate_images(self, entries: dict) -> None:
        for entry in entries.values():
            if entry.get('type') in ('IMAGE', 'GIF'):
                reader = QImageReader(entry.get('file_path', ''))
                size = reader.size()
                if not reader.canRead() or not 0 < size.width() * size.height() <= 16_777_216:
                    raise ValueError('Scene output image is invalid or exceeds 16 megapixels')

    def close(self) -> None:
        """Dispose native renderers and clock before referenced scene assets."""
        if self.closed:
            return
        self.closed = True
        if self.view is not None:
            self.view.close()
            self.view.deleteLater()
        self.manager.clear()
