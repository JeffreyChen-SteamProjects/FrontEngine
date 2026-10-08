"""Identity-safe native window following in one physical coordinate space."""
from __future__ import annotations

from dataclasses import dataclass
import sys
from uuid import uuid4
import weakref

from PySide6.QtCore import QObject, QTimer, QEvent, Signal

from frontengine.utils.window_pin.window_layout import window_geometry
from frontengine.utils.window_pin.monitor_move import clamp_into


class Win32FollowBackend:
    """Tag only explicitly selected targets; a destroyed/reused HWND loses the private cookie."""

    def __init__(self) -> None:
        self._user = None

    @staticmethod
    def available() -> bool:
        """Require Windows rather than claiming an unverified cross-platform identity adapter."""
        return sys.platform == 'win32'

    def _api(self):
        import ctypes
        from ctypes import wintypes
        if not self.available():
            raise ValueError('Window following requires Windows; other native adapters are not verified')
        if getattr(self, '_user', None) is not None:
            return self._user
        user = ctypes.WinDLL('user32', use_last_error=True)
        user.SetPropW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.HANDLE]
        user.SetPropW.restype = wintypes.BOOL
        user.GetPropW.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
        user.GetPropW.restype = wintypes.HANDLE
        user.RemovePropW.argtypes = user.GetPropW.argtypes
        user.RemovePropW.restype = wintypes.HANDLE
        user.IsWindow.argtypes = user.IsIconic.argtypes = user.IsWindowVisible.argtypes = [wintypes.HWND]
        user.IsWindow.restype = user.IsIconic.restype = user.IsWindowVisible.restype = wintypes.BOOL
        user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        user.GetWindowThreadProcessId.restype = wintypes.DWORD
        self._user = user
        return user

    def bind(self, handle: int) -> dict:
        """Allocate a reversible property only after a valid PID/thread identity is obtained."""
        import ctypes
        from ctypes import wintypes
        user = self._api()
        pid = wintypes.DWORD()
        thread = int(user.GetWindowThreadProcessId(handle, ctypes.byref(pid)))
        if not user.IsWindow(handle) or not thread or not pid.value:
            raise ValueError('Selected target window has closed')
        name = 'FrontEngine.Follow.' + uuid4().hex
        if not user.SetPropW(handle, name, wintypes.HANDLE(1)):
            raise ValueError('Target identity registration denied (possibly an elevated window)')
        return dict(handle=int(handle), property=name, pid=int(pid.value), thread=thread)

    def snapshot(self, identity: dict) -> dict | None:
        """Return geometry only if the original cookie and PID/thread still match."""
        import ctypes
        from ctypes import wintypes
        user = self._api()
        handle = identity['handle']
        pid = wintypes.DWORD()
        thread = int(user.GetWindowThreadProcessId(handle, ctypes.byref(pid)))
        if (not user.IsWindow(handle) or user.GetPropW(handle, identity['property']) != 1 or
                (int(pid.value), thread) != (identity['pid'], identity['thread'])):
            return None
        if not user.IsWindowVisible(handle) and not user.IsIconic(handle):
            return None
        rectangle = window_geometry(handle)
        if rectangle is None:
            raise ValueError('Target window geometry is unavailable')
        work = self._work_area(handle)
        if user.GetPropW(handle, identity['property']) != 1:
            return None
        return dict(rect=rectangle, minimized=bool(user.IsIconic(handle)), work=work)

    def release(self, identity: dict) -> None:
        """Remove only our matching private cookie, never a reused target's property."""
        user = self._api()
        if user.IsWindow(identity['handle']) and user.GetPropW(identity['handle'], identity['property']) == 1:
            user.RemovePropW(identity['handle'], identity['property'])

    def _work_area(self, handle: int) -> tuple:
        import ctypes
        from ctypes import wintypes
        class MonitorInfo(ctypes.Structure):
            _fields_ = [('cbSize', wintypes.DWORD), ('rcMonitor', wintypes.RECT),
                        ('rcWork', wintypes.RECT), ('dwFlags', wintypes.DWORD)]
        user = self._api()
        user.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
        user.MonitorFromWindow.restype = wintypes.HANDLE
        user.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
        user.GetMonitorInfoW.restype = wintypes.BOOL
        monitor = user.MonitorFromWindow(handle, 2)
        info = MonitorInfo()
        info.cbSize = ctypes.sizeof(info)
        if not monitor or not user.GetMonitorInfoW(monitor, ctypes.byref(info)):
            raise ValueError('Target monitor work area is unavailable')
        area = info.rcWork
        return area.left, area.top, area.right-area.left, area.bottom-area.top

    @staticmethod
    def geometry(widget) -> tuple:
        """Read the overlay's physical frame, never feed logical Qt positions to Win32."""
        rectangle = window_geometry(int(widget.winId()))
        if rectangle is None:
            raise ValueError('Overlay geometry is unavailable')
        return rectangle

    def move(self, widget, x: int, y: int) -> bool:
        """Move without sizing/activation; Qt processes monitor DPI changes itself."""
        import ctypes
        from ctypes import wintypes
        user = self._api()
        user.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int,
                                      ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
        user.SetWindowPos.restype = wintypes.BOOL
        return bool(user.SetWindowPos(int(widget.winId()), None, x, y, 0, 0, 0x0001 | 0x0004 | 0x0010))


@dataclass
class FollowBinding:
    """Temporary binding; never restore native handles across application sessions."""
    widget: object
    identity: dict
    anchor: tuple[float, float]
    desired_visible: bool
    hidden_by_target: bool = False
    changing_visibility: bool = False


class WindowFollowService(QObject):
    """Poll bounded temporary bindings, preserving explicit user/batch visibility choices."""
    changed = Signal()
    failed = Signal(str)

    def __init__(self, parent=None, *, backend=None) -> None:
        super().__init__(parent)
        self.backend = backend or Win32FollowBackend()
        self.bindings, self.closed, self.group_hidden = {}, False, False
        self.connected = weakref.WeakSet()
        self.timer = QTimer(self)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.poll)

    def bind(self, widget, handle: int) -> None:
        """Bind initial proportional offset; reject self-follow and release on every failure."""
        if self.closed or (len(self.bindings) >= 64 and id(widget) not in self.bindings):
            raise ValueError('Window following is closed or reached 64 bindings')
        if handle == int(widget.winId()):
            raise ValueError('An overlay cannot follow itself')
        identity = self.backend.bind(handle)
        try:
            target = self.backend.snapshot(identity)
            if target is None or target['minimized']:
                raise ValueError('Restore the target window before binding')
            x, y, width, height = target['rect']
            overlay = self.backend.geometry(widget)
            if width <= 0 or height <= 0:
                raise ValueError('Target size is invalid')
            anchor = ((overlay[0]-x)/width, (overlay[1]-y)/height)
            self.unbind(widget, restore=False)
            self.bindings[id(widget)] = FollowBinding(weakref.ref(widget), identity, anchor, widget.isVisible())
            widget.installEventFilter(self)
            if widget not in self.connected:
                self.connected.add(widget)
                widget.destroyed.connect(lambda _object=None, key=id(widget): self._unbind_key(key, False))
            self.timer.start()
            self.changed.emit()
        except Exception:
            self.backend.release(identity)
            raise

    def unbind(self, widget, *, restore: bool = True) -> None:
        """Release one target cookie and optionally restore a target-hidden float window."""
        self._unbind_key(id(widget), restore)

    def _unbind_key(self, key: int, restore: bool) -> None:
        binding = self.bindings.pop(key, None)
        if binding is None:
            return
        try:
            self.backend.release(binding.identity)
        except (OSError, ValueError, RuntimeError) as error:
            self.failed.emit(str(error))
        widget = binding.widget()
        if widget is not None:
            try:
                widget.removeEventFilter(self)
                if restore and binding.hidden_by_target and binding.desired_visible and not self.group_hidden:
                    widget.show()
            except RuntimeError:
                pass
        if not self.bindings:
            self.timer.stop()
        self.changed.emit()

    def eventFilter(self, watched, event) -> bool:
        binding = self.bindings.get(id(watched))
        if binding is not None:
            if event.type() == QEvent.Type.Close:
                self._unbind_key(id(watched), False)
            elif not binding.changing_visibility and event.type() in (QEvent.Type.Hide, QEvent.Type.Show):
                binding.desired_visible = event.type() == QEvent.Type.Show
        return False

    def set_group_hidden(self, hidden: bool) -> None:
        """An explicit hide-all must not be undone when a minimized target returns."""
        self.group_hidden = hidden
        for binding in self.bindings.values():
            binding.desired_visible = not hidden
        if not hidden:
            self.poll()

    def poll(self) -> None:
        """Stop on lost identity; move only changed origins and never resize native targets."""
        for key, binding in list(self.bindings.items()):
            widget = binding.widget()
            try:
                if widget is None:
                    self._unbind_key(key, False)
                    continue
                target = self.backend.snapshot(binding.identity)
                if target is None:
                    self._unbind_key(key, True)
                    continue
                self._update(binding, widget, target)
            except (OSError, ValueError, RuntimeError) as error:
                self.failed.emit(str(error))
                self._unbind_key(key, True)

    def _update(self, binding: FollowBinding, widget, target: dict) -> None:
        if target['minimized'] or self.group_hidden:
            if widget.isVisible():
                self._visibility(binding, widget, False)
                binding.hidden_by_target = True
            return
        x, y, width, height = target['rect']
        current = self.backend.geometry(widget)
        planned = (round(x + width*binding.anchor[0]), round(y + height*binding.anchor[1]), *current[2:])
        planned = clamp_into(planned, target['work'])
        if current[:2] != planned[:2] and not self.backend.move(widget, *planned[:2]):
            raise ValueError('Following overlay movement failed')
        if binding.hidden_by_target and binding.desired_visible:
            self._visibility(binding, widget, True)
        binding.hidden_by_target = False

    @staticmethod
    def _visibility(binding: FollowBinding, widget, visible: bool) -> None:
        binding.changing_visibility = True
        try:
            widget.setVisible(visible)
        finally:
            binding.changing_visibility = False

    def stop(self) -> None:
        """Detach all targets without reopening overlays during shutdown."""
        self.closed = True
        self.detach_all()

    def detach_all(self) -> None:
        """Release bindings after a control-center close-all, allowing later new bindings."""
        for key in list(self.bindings):
            self._unbind_key(key, False)
        self.timer.stop()
