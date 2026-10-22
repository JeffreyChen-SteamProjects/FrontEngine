"""Background scene preparation and GUI-thread scene/layer action dispatch."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from threading import Event

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal
from PySide6.QtGui import QGuiApplication, QImage

from frontengine.show.scene.scene import SceneManager
from frontengine.show.scene.compositor_view import SceneCompositorView
from frontengine.show.scene.extend_graphic_view import ExtendGraphicView
from frontengine.user_setting.user_setting_file import user_setting_dict
from frontengine.utils.actions.deferred_action import DeferredAction
from frontengine.utils.scene_format.scene_action_values import scene_request, layer_changes
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.scene_format.scene_editor_document import validate_geometry
from frontengine.utils.scene_format.scene_source import PreparedScene, read_scene_source


def close_playback(manager: SceneManager) -> None:
    """Stop views before deleting the proxies they read, retaining list identity."""
    for view in tuple(manager.view_list):
        try:
            view.close()
            view.deleteLater()
        except RuntimeError:
            continue
    manager.view_list.clear()
    manager.clear()


def transition_frames(manager: SceneManager) -> dict[str, QImage]:
    """Retain bounded outgoing surfaces before their native resources close."""
    from shiboken6 import isValid
    frames = {}
    for view in manager.view_list[:8]:
        if isValid(view) and isinstance(view, SceneCompositorView) and view.isVisible():
            frames[view.screen().name()] = view.output_frame().scaled(1920, 1080, Qt.AspectRatioMode.KeepAspectRatio)
    return frames


def prepare_playback(entries: dict, monitors: list) -> SceneManager:
    """Build hidden playback; failures close every candidate and preserve the old scene."""
    candidate = SceneManager()
    try:
        for key, entry in entries.items():
            for field in ('file_path', 'text_file', 'script_path'):
                if entry.get(field) and not Path(entry[field]).is_file():
                    raise ValueError(f'Missing scene resource: {entry[field]}')
            candidate.add_entry(key, entry)
        for monitor in monitors:
            candidate.open_native_widgets(monitor, show=False)
            if not candidate.widget_list:
                continue
            view = (SceneCompositorView(candidate.graphic_scene, user_setting_dict.get('render_backend', 'auto'))
                    if candidate.supports_composition() else ExtendGraphicView(candidate.graphic_scene))
            candidate.view_list.append(view)
            if monitor is not None:
                view.setScreen(monitor)
                view.move(monitor.availableGeometry().topLeft())
        return candidate
    except (OSError, ValueError, RuntimeError):
        close_playback(candidate)
        raise


class _SceneSignals(QObject):
    finished = Signal(object, str)


class _SceneRead(QRunnable):
    def __init__(self, function, cancel: Event, signals: _SceneSignals) -> None:
        super().__init__()
        self.function, self.cancel, self.signals = function, cancel, signals

    def run(self) -> None:
        result, error = None, ''
        try:
            if not self.cancel.is_set():
                result = self.function()
        except (OSError, ValueError, RuntimeError, RecursionError) as exception:
            error = str(exception)
        if self.cancel.is_set() and result is not None:
            result.close()
            result = None
        self.signals.finished.emit(result, error)


class SceneActions(QObject):
    """Own one background read and one latest queued request; widgets stay on GUI thread."""

    status_changed = Signal(str)

    def __init__(self, page, *, reader=read_scene_source, builder=prepare_playback) -> None:
        super().__init__(page)
        self.page, self.reader, self.builder = page, reader, builder
        self.pending = None
        self.wanted = None
        self.closed = False
        self.prepared: PreparedScene | None = None
        self.queued_layers: list[tuple[DeferredAction, str, str]] = []
        self.page.visual_editor.document.changed.connect(self._synchronize)

    def request(self, value: str, *, load_only: bool = False) -> DeferredAction:
        """Load or play the latest request; superseded receipts resolve as failures."""
        if self.closed:
            raise ValueError('Scene actions are closed')
        path, screen = scene_request(value, load_only=load_only)
        entries = deepcopy(self.page.visual_editor.document.entries) if not path else None
        return self._enqueue(path, screen, load_only, entries, not path)

    def request_entries(self, entries: dict, screen: str | int = 'primary') -> DeferredAction:
        """Play validated in-memory templates through the same candidate transaction."""
        if self.closed:
            raise ValueError('Scene actions are closed')
        _path, screen = scene_request(json.dumps({'screen': screen}))
        validated = validate_geometry(entries)
        if len(validated) > 256:
            raise ValueError('Automated scenes support at most 256 layers')
        return self._enqueue('', screen, False, validated, False)

    def cancel_request(self, operation: DeferredAction) -> None:
        """Cancel one owner request without stopping existing or newer playback."""
        if self.wanted is not None and self.wanted[0] is operation:
            self.wanted = None
            operation.finish(False, 'Scene request cancelled')
            self._cancel_layers('Scene request cancelled')
        elif self.pending is not None and self.pending['request'][0] is operation:
            self.pending['cancel'].set()
            operation.finish(False, 'Scene request cancelled')
            if self.wanted is None:
                self._cancel_layers('Scene request cancelled')

    def _enqueue(self, path: str, screen, load_only: bool, entries, current: bool) -> DeferredAction:
        self._cancel_layers('Superseded by a newer scene request')
        operation = DeferredAction(self)
        operation.finished.connect(lambda _success, _error: operation.deleteLater())
        if self.wanted is not None:
            self.wanted[0].finish(False, 'Superseded by a newer scene request')
        if self.pending is not None:
            self.pending['cancel'].set()
            self.pending['request'][0].finish(False, 'Superseded by a newer scene request')
        self.wanted = (operation, path, screen, load_only, entries, current)
        self._launch()
        return operation

    def _launch(self) -> None:
        if self.pending is not None or self.wanted is None or self.closed:
            return
        request, self.wanted = self.wanted, None
        _operation, path, _screen, _load, entries, _current = request
        cancel, signals = Event(), _SceneSignals()
        signals.finished.connect(self._finished, Qt.ConnectionType.QueuedConnection)
        self.pending = {'request': request, 'cancel': cancel, 'signals': signals}
        function = (lambda: self.reader(path)) if path else lambda: PreparedScene(validate_geometry(entries))
        QThreadPool.globalInstance().start(_SceneRead(function, cancel, signals))
        self.status_changed.emit('')

    def _monitors(self, selection: str | int) -> list:
        screens = QGuiApplication.screens()
        if selection == 'primary':
            return [QGuiApplication.primaryScreen()]
        if selection == 'all':
            return screens or [None]
        if selection >= len(screens):
            raise ValueError('The selected scene screen is unavailable')
        return [screens[selection]]

    def _finished(self, prepared: PreparedScene | None, error: str) -> None:
        pending, self.pending = self.pending, None
        operation, _path, screen, load_only, _entries, current = pending['request']
        if pending['cancel'].is_set() or self.closed:
            if prepared is not None:
                prepared.close()
        elif error:
            operation.finish(False, error)
            self.status_changed.emit(error)
        else:
            try:
                self._adopt(prepared, screen, load_only, current)
            except (OSError, ValueError, RuntimeError) as exception:
                prepared.close()
                operation.finish(False, str(exception))
                self.status_changed.emit(str(exception))
            else:
                operation.finish(True)
                self.status_changed.emit('')
                self._finish_layers()
        if operation.result is False and not pending['cancel'].is_set():
            self._cancel_layers('The preceding scene action did not complete')
        self._launch()

    def _adopt(self, prepared: PreparedScene, screen, load_only: bool, current: bool) -> None:
        if current and prepared.entries != self.page.visual_editor.document.entries:
            raise ValueError('The editor changed while scene playback was being prepared')
        candidate = None if load_only else self.builder(prepared.entries, self._monitors(screen))
        manager = self.page.scene
        previous_frames = transition_frames(manager) if candidate is not None else {}
        close_playback(manager)
        if candidate is not None:
            manager.graphic_scene = candidate.graphic_scene
            for name in ('widget_list', 'view_list', 'native_widgets', 'puppet_settings'):
                getattr(manager, name)[:] = getattr(candidate, name)
            manager.layer_settings.update(candidate.layer_settings)
        if not current:
            self.page.visual_editor.document.reset(prepared.entries)
            previous, self.prepared = self.prepared, prepared
            if previous is not None:
                previous.close()
        else:
            prepared.close()
        for view in manager.view_list:
            if isinstance(view, SceneCompositorView):
                view.begin_transition(previous_frames.get(view.screen().name()))
            view.showMaximized()
        for widget in manager.native_widgets:
            setting = manager.layer_settings.get(widget.scene_layer_key, {})
            widget.setVisible(setting.get('visible', True))

    def layer(self, action: str, value: str) -> bool | DeferredAction:
        """Change a named editor layer with undo; playback tracks the same document."""
        if self.closed:
            raise ValueError('Scene actions are closed')
        key, changes = layer_changes(action, value)
        if self.pending is not None or self.wanted is not None:
            if len(self.queued_layers) >= 200:
                raise ValueError('At most 200 layer actions can wait for scene loading')
            operation = DeferredAction(self)
            operation.finished.connect(lambda _success, _error: operation.deleteLater())
            self.queued_layers.append((operation, action, value))
            return operation
        document = self.page.visual_editor.document
        if key not in document.entries:
            raise ValueError(f'Unknown scene layer: {key}')
        if document.entries[key].get('locked'):
            raise ValueError(f'Scene layer is locked: {key}')
        before = deepcopy(document.entries)
        after = deepcopy(before)
        after[key].update(changes)
        try:
            self.page.scene.synchronize_layers(after)
            document.update(key, changes, 'Rule layer action')
        except (ValueError, RuntimeError):
            self.page.scene.synchronize_layers(before)
            raise
        return True

    def _finish_layers(self) -> None:
        queued, self.queued_layers = self.queued_layers, []
        for operation, action, value in queued:
            try:
                success = self.layer(action, value)
            except (OSError, ValueError, RuntimeError) as error:
                operation.finish(False, str(error))
                self.status_changed.emit(str(error))
            else:
                operation.finish(success is not False)

    def _cancel_layers(self, error: str) -> None:
        for operation, _action, _value in self.queued_layers:
            operation.finish(False, error)
        self.queued_layers.clear()

    def _synchronize(self, entries: dict) -> None:
        try:
            self.page.scene.synchronize_layers(entries)
        except (ValueError, RuntimeError) as error:
            front_engine_logger.warning(f'[SceneActions] playback update failed: {error}')
            self.status_changed.emit(str(error))

    def stop_playback(self, _value: str = '') -> bool:
        """Cancel pending starts and stop playback; keep editor assets available."""
        if self.pending is not None:
            self.pending['cancel'].set()
            self.pending['request'][0].finish(False, 'Scene playback stopped')
        if self.wanted is not None:
            self.wanted[0].finish(False, 'Scene playback stopped')
            self.wanted = None
        self._cancel_layers('Scene playback stopped')
        close_playback(self.page.scene)
        return True

    def shutdown(self) -> None:
        """Cancel work, stop playback/previews, then release the editor asset lease."""
        self.closed = True
        self.stop_playback()
        self.page.visual_editor.media_preview.shutdown()
        self.page.visual_editor.timeline.shutdown()
        self.page.visual_editor.canvas.clear()
        if self.prepared is not None:
            self.prepared.close()
            self.prepared = None
