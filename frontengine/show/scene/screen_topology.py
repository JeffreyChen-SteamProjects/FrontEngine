"""Suspend disconnected scene targets and restore them without duplicating decoders."""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication
from shiboken6 import isValid

from frontengine.utils.multi_language.retranslate import translate


def screen_identity(screen):
    if screen is None:
        return ('primary',)
    serial = screen.serialNumber()
    return ((screen.manufacturer(), screen.model(), serial) if serial else (screen.name(),))


@dataclass
class ScreenSlot:
    identity: tuple
    name: str
    screen: object
    view: object
    visible: bool = True
    enabled: bool = True


class SceneScreenTopology(QObject):
    """Own signal subscriptions for one playback transaction, including empty targets."""
    def __init__(self, runtime, screens, views, *, application=None, view_factory=None, alive=isValid):
        super().__init__(runtime)
        self.runtime = runtime
        self.application = application or QGuiApplication.instance()
        self.view_factory = view_factory
        self.alive = alive
        self.views = views
        self.slots = [ScreenSlot(screen_identity(screen), screen.name() if screen else 'primary', screen, view)
                      for screen, view in zip(screens, views)]
        self.started, self.closed, self.group_hidden = False, False, False
        self._geometry_connections = {}

    def start(self, views=None):
        if self.started or self.closed:
            return
        if views is not None:
            self.views = views
        self.started = True
        self.application.screenRemoved.connect(self.screen_removed)
        self.application.screenAdded.connect(self.screen_added)
        self.application.primaryScreenChanged.connect(self.retry)
        for slot in self.slots:
            self._watch(slot.screen)
            self._bind_view(slot)

    def _bind_view(self, slot):
        signal = getattr(slot.view, 'closed', None)
        if hasattr(signal, 'connect'):
            view = slot.view
            signal.connect(lambda: self._view_closed(slot, view))

    def _view_closed(self, slot, view):
        if not self.closed and slot.view is view:
            slot.visible, slot.enabled, slot.view = False, False, None
            self.views[:] = [item for item in self.views if item is not view]

    def _watch(self, screen):
        if screen is None or id(screen) in self._geometry_connections:
            return
        callback = lambda *_args, target=screen: self._resize(target)
        screen.availableGeometryChanged.connect(callback)
        self._geometry_connections[id(screen)] = (screen, callback)

    def _unwatch(self, screen):
        binding = self._geometry_connections.pop(id(screen), None)
        if binding is not None:
            try:
                binding[0].availableGeometryChanged.disconnect(binding[1])
            except RuntimeError:
                pass

    def _resize(self, screen):
        for slot in self.slots:
            if slot.screen is screen and slot.view is not None and self.alive(slot.view):
                slot.view.move(screen.availableGeometry().topLeft())
                if slot.view.isVisible():
                    slot.view.showMaximized()

    def screen_removed(self, screen):
        if self.closed:
            return
        self._unwatch(screen)
        for slot in self.slots:
            if slot.screen is not screen:
                continue
            view = slot.view
            slot.screen, slot.view = None, None
            if view is not None:
                self.views[:] = [item for item in self.views if item is not view]
                if self.alive(view):
                    if not self.group_hidden:
                        slot.visible = view.isVisible()
                    view.close()
                    view.deleteLater()
            self.runtime.failed.emit(translate('scene3d_screen_removed', 'Display disconnected; its scene is suspended: ') + slot.name)

    def screen_added(self, screen):
        if not self.closed:
            self._restore(screen)

    def retry(self, *_args):
        if not self.closed:
            for screen in self.application.screens():
                self._restore(screen)

    def _restore(self, screen):
        for slot in self.slots:
            if not slot.enabled or slot.view is not None or (slot.identity != screen_identity(screen) and
                    not (slot.identity == ('primary',) and screen is self.application.primaryScreen())):
                continue
            view = None
            try:
                factory = self.view_factory
                if factory is None:
                    from .view3d import Scene3DView
                    factory = Scene3DView
                view = factory(self.runtime)
                view.setScreen(screen)
                view.move(screen.availableGeometry().topLeft())
                view.prime()
                slot.screen, slot.view = screen, view
                self.views.append(view)
                self._bind_view(slot)
                self._watch(screen)
                if slot.visible and not self.group_hidden:
                    view.showMaximized()
            except Exception as error:
                if view is not None and self.alive(view):
                    view.close()
                    view.deleteLater()
                slot.screen, slot.view = None, None
                self.views[:] = [item for item in self.views if item is not view]
                self.runtime.failed.emit(f'{slot.name}: {error}')

    def set_group_hidden(self, hidden):
        self.group_hidden = bool(hidden)
        for slot in self.slots:
            if slot.view is not None and self.alive(slot.view):
                if hidden:
                    slot.view.hide()
                elif slot.visible:
                    slot.view.showMaximized()

    def close(self):
        if self.closed:
            return
        self.closed = True
        if self.started:
            for signal, callback in ((self.application.screenRemoved, self.screen_removed),
                                     (self.application.screenAdded, self.screen_added),
                                     (self.application.primaryScreenChanged, self.retry)):
                signal.disconnect(callback)
        for screen, _callback in tuple(self._geometry_connections.values()):
            self._unwatch(screen)
        self.slots.clear()
