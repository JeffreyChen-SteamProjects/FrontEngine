"""Storage-free callback admission, owned Qt jobs, and asynchronous retirement."""
from __future__ import annotations

from enum import Enum
from functools import wraps
from inspect import Parameter, signature

from PySide6.QtCore import QObject, QThreadPool, QTimer, Signal
from shiboken6 import isValid

class LifetimeClosed(RuntimeError):
    pass


class CloseDisposition(Enum):
    REFUSED = "refused"
    DRAINING = "draining"
    CLOSED = "closed"


class RuntimeState(Enum):
    LIVE = "live"
    PREPARING = "preparing"
    RETIRING = "retiring"
    CLOSED = "closed"


_retiring = set()


def captured_lifetime(owner):
    """Resolve a supplied owner during construction, never from ambient settings."""
    current = owner
    while current is not None:
        lifetime = getattr(current, 'lifetime', None) or getattr(current, '_frontengine_lifetime', None)
        if lifetime is not None:
            return lifetime
        current = current.parent() if isinstance(current, QObject) else None
    raise LifetimeClosed('This object requires an explicit work lifetime')


def _slot_arity(callback, *, method=False):
    """Preserve Qt's trailing-argument adaptation when a variadic guard hides the slot signature."""
    try:
        parameters = tuple(signature(callback).parameters.values())
    except (TypeError, ValueError):
        return None
    if any(parameter.kind is Parameter.VAR_POSITIONAL for parameter in parameters):
        return None
    positional = sum(parameter.kind in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD)
                     for parameter in parameters)
    return positional - int(method)


def owned_callback(method):
    """Reject a queued method before it can read or mutate its retired generation."""
    arity = _slot_arity(method, method=True)
    @wraps(method)
    def call(self, *args, **kwargs):
        lifetime = captured_lifetime(self)
        return lifetime.dispatch(method.__get__(self, type(self)), args[:arity], kwargs)
    return call


class _ActionCancelled(RuntimeError):
    pass


def owned_action(method):
    """Admit new UI actions only while live; never replay rejected user intent."""
    arity = _slot_arity(method, method=True)
    @wraps(method)
    def call(self, *args, **kwargs):
        lifetime = captured_lifetime(self)
        if not lifetime.accepting:
            return None
        try:
            return method(self, *args[:arity], **kwargs)
        except _ActionCancelled:
            return None
    return call


class OwnedWidgetList(list):
    def __init__(self, lifetime):
        super().__init__()
        self.lifetime = lifetime

    def append(self, widget):
        self.lifetime.adopt(widget)
        super().append(widget)

    def extend(self, widgets):
        for widget in widgets:
            self.append(widget)

    def insert(self, index, widget):
        self.lifetime.adopt(widget)
        super().insert(index, widget)


class WorkLifetime(QObject):
    """A host-held default generation; retire only after domain saves and closes."""
    finished = Signal()
    failed = Signal(object)

    def __init__(self):
        super().__init__()
        self.state = RuntimeState.LIVE
        self._pools = {}
        self._roots = {}
        self._pending = []
        self._stoppers = []
        self._connections = []
        self._deferred = []
        self._deleting = False
        self.error = None
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(10)
        self._poll_timer.timeout.connect(self._poll)

    @property
    def accepting(self):
        return self.state is RuntimeState.LIVE

    @property
    def closed(self):
        return self.state is RuntimeState.CLOSED

    def require_live(self):
        if not self.accepting:
            raise LifetimeClosed('The settings lifetime is not accepting new work')

    def after_dialog(self, result):
        if not self.accepting:
            raise _ActionCancelled('The action owner retired while its dialog was open')
        return result

    def guard(self, callback):
        arity = _slot_arity(callback)
        @wraps(callback)
        def guarded(*args, **kwargs):
            return self.dispatch(callback, args[:arity], kwargs)
        return guarded

    def dispatch(self, callback, args=(), kwargs=None):
        if self.accepting:
            return callback(*args, **(kwargs or {}))
        if self.state is RuntimeState.PREPARING:
            self._deferred.append((callback, args, kwargs))
        return None

    def connect_owned(self, signal, callback, connection_type=None):
        guarded = self.guard(callback)
        if connection_type is None:
            signal.connect(guarded)
        else:
            signal.connect(guarded, connection_type)
        self._connections.append((signal, guarded))
        return guarded

    def adopt(self, root):
        self.require_live()
        root._frontengine_lifetime = self
        self._roots[id(root)] = root
        return root

    def pool(self, group='default'):
        if group not in self._pools:
            self.require_live()
            pool = QThreadPool(self)
            if group == 'comparison':
                pool.setMaxThreadCount(2)
            self._pools[group] = pool
        return self._pools[group]

    def submit(self, job, group='default'):
        self.require_live()
        self.pool(group).start(job)

    def register_pending(self, predicate):
        self.require_live()
        self._pending.append(predicate)

    def register_stop(self, stop):
        self.require_live()
        self._stoppers.append(stop)

    def begin_prepare(self):
        self.require_live()
        self.state = RuntimeState.PREPARING

    def cancel_prepare(self):
        if self.state is RuntimeState.PREPARING:
            self.state = RuntimeState.LIVE
            pending, self._deferred = self._deferred, []
            for callback, args, kwargs in pending:
                QTimer.singleShot(0, self, lambda cb=callback, a=args, k=kwargs: self.dispatch(cb, a, k))

    def block(self, error, *, report=False):
        self.error = error
        if report:
            self.failed.emit(error)

    def close(self):
        if self.closed:
            return CloseDisposition.CLOSED
        if self.state is not RuntimeState.RETIRING:
            self.state = RuntimeState.RETIRING
            self._deferred.clear()
            _retiring.add(self)
            for signal, callback in self._connections:
                try:
                    signal.disconnect(callback)
                except (RuntimeError, TypeError):
                    pass
            self._connections.clear()
            from frontengine.utils.multi_language.retranslate import retranslator
            retranslator.retire(self, tuple(self._roots.values()))
            self._poll_timer.start()
            QTimer.singleShot(0, self, self._poll)
        return CloseDisposition.DRAINING

    def pending(self):
        return any(pool.activeThreadCount() for pool in self._pools.values()) or any(check() for check in self._pending)

    def _poll(self):
        if self.state is not RuntimeState.RETIRING or self.error is not None:
            return
        while self._stoppers:
            try:
                self._stoppers[0]()
            except Exception as error:
                self.block(error, report=True)
                return
            self._stoppers.pop(0)
        if not self._deleting:
            if self.pending():
                return
            self._deleting = True
            for root in tuple(self._roots.values()):
                if isValid(root):
                    root.deleteLater()
            QTimer.singleShot(0, self, self._poll)
            return
        if any(isValid(root) for root in self._roots.values()):
            return
        if not self._release():
            return
        self._roots.clear()
        self._pending.clear()
        self._poll_timer.stop()
        self.state = RuntimeState.CLOSED
        _retiring.discard(self)
        self.finished.emit()

    def _release(self):
        return True
