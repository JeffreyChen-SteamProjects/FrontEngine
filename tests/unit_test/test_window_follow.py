"""Injected window identity and movement; no native handles or existing apps touched."""
from copy import deepcopy

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtWidgets import QWidget

from frontengine.utils.window_pin.follow_window import WindowFollowService
from frontengine.ui.dialog.window_follow_dialog import WindowFollowDialog


class Backend:
    def __init__(self):
        self.target = {'rect': (100, 100, 400, 300), 'minimized': False, 'work': (0, 0, 2000, 1600)}
        self.moves, self.released = [], []
        self.valid = True

    def available(self):
        return True

    def bind(self, handle):
        return {'handle': handle, 'cookie': 123}

    def snapshot(self, identity):
        return deepcopy(self.target) if self.valid and identity['cookie'] == 123 else None

    def release(self, identity):
        self.released.append(identity)

    def geometry(self, widget):
        return widget.geometry().getRect()

    def move(self, widget, x, y):
        self.moves.append((x, y))
        widget.move(x, y)
        return True


def setup():
    backend = Backend()
    service = WindowFollowService(backend=backend)
    widget = QWidget()
    widget.setWindowFlag(Qt.WindowType.FramelessWindowHint)
    widget.setGeometry(300, 200, 120, 80)
    widget.show()
    service.bind(widget, 99999999)
    return backend, service, widget


def cleanup(service, widget):
    service.stop()
    widget.close()
    widget.deleteLater()
    QCoreApplication.sendPostedEvents(widget, QEvent.Type.DeferredDelete)


def test_relative_resize_move_clamp_and_no_repeated_native_updates():
    backend, service, widget = setup()
    try:
        backend.target['rect'] = (200, 150, 800, 600)
        service.poll()
        assert widget.pos().toTuple() == (600, 350)
        assert widget.size().toTuple() == (120, 80)
        service.poll()
        assert backend.moves == [(600, 350)]
        backend.target['work'] = (0, 0, 500, 300)
        service.poll()
        assert widget.pos().toTuple() == (380, 220)
    finally:
        cleanup(service, widget)


def test_minimize_restore_respects_explicit_hide_and_group_hide():
    backend, service, widget = setup()
    try:
        backend.target['minimized'] = True
        service.poll()
        assert not widget.isVisible()
        backend.target['minimized'] = False
        service.poll()
        assert widget.isVisible()
        widget.hide()
        backend.target['minimized'] = True
        service.poll()
        backend.target['minimized'] = False
        service.poll()
        assert not widget.isVisible()
        widget.show()
        backend.target['minimized'] = True
        service.poll()
        service.set_group_hidden(True)
        backend.target['minimized'] = False
        service.poll()
        assert not widget.isVisible()
        widget.show()
        service.set_group_hidden(False)
        assert widget.isVisible()
    finally:
        cleanup(service, widget)


def test_lost_or_reused_identity_detaches_and_cannot_follow_new_geometry():
    backend, service, widget = setup()
    try:
        backend.target['minimized'] = True
        service.poll()
        backend.valid = False
        backend.target['rect'] = (900, 900, 500, 500)
        service.poll()
        assert not service.bindings and not service.timer.isActive()
        assert widget.isVisible() and not backend.moves and len(backend.released) == 1
    finally:
        cleanup(service, widget)


def test_rebind_close_and_detach_all_release_cookies_without_permanent_shutdown():
    backend, service, widget = setup()
    try:
        service.bind(widget, 99999998)
        assert len(service.bindings) == 1 and len(backend.released) == 1
        service.detach_all()
        assert not service.closed and not service.timer.isActive()
        service.bind(widget, 99999997)
        widget.close()
        assert not service.bindings and not service.timer.isActive()
        assert len(backend.released) == 3
        assert len(service.connected) == 1
    finally:
        cleanup(service, widget)


def test_unbind_restores_only_target_hidden_window_and_failed_bind_releases_identity():
    backend, service, widget = setup()
    try:
        backend.target['minimized'] = True
        service.poll()
        service.unbind(widget)
        assert widget.isVisible()
        with pytest.raises(ValueError, match='Restore'):
            service.bind(widget, 99999999)
        assert len(backend.released) == 2
        with pytest.raises(ValueError, match='itself'):
            service.bind(widget, int(widget.winId()))
    finally:
        cleanup(service, widget)


def test_manager_uses_only_registered_overlays_and_explicit_target():
    backend, service, widget = setup()
    service.detach_all()
    dialog = WindowFollowDialog(service, lambda: [[widget, widget]], lister=lambda: [(99999999, 'own fake target')])
    try:
        dialog.show()
        assert dialog.overlays.count() == dialog.targets.count() == 1
        assert not service.bindings
        dialog._bind()
        assert len(service.bindings) == 1
        dialog._detach()
        assert not service.bindings
        dialog.close()
    finally:
        dialog.deleteLater()
        QCoreApplication.sendPostedEvents(dialog, QEvent.Type.DeferredDelete)
        cleanup(service, widget)
