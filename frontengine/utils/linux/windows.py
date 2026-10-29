"""EWMH X11 client requests; native Wayland windows are explicitly unsupported."""
from __future__ import annotations
from contextlib import contextmanager
from frontengine.utils.linux.capabilities import x11_reason

last_error = ''


def available() -> bool:
    if x11_reason():
        return False
    try:
        from Xlib import display
        return bool(display.Display)
    except ImportError:
        return False


@contextmanager
def connection():
    """Close each native connection on every path; never reuse stale XIDs across requests."""
    reason = x11_reason()
    if reason:
        raise ValueError(reason)
    from Xlib import display
    client = display.Display()
    try:
        yield client, client.screen().root
    finally:
        client.close()


def _property(client, window, name: str):
    value = window.get_full_property(client.intern_atom(name), 0)
    return value.value if value is not None else []


def _geometry(client, root, window) -> tuple[int, int, int, int]:
    rect = window.get_geometry()
    origin = root.translate_coords(window, 0, 0)
    extent = _property(client, window, '_NET_FRAME_EXTENTS')
    left, right, top, bottom = extent[:4] if len(extent) == 4 else (0, 0, 0, 0)
    return int(origin.x - left), int(origin.y - top), int(rect.width + left + right), int(rect.height + top + bottom)


def _failed(error: Exception, fallback):
    global last_error
    last_error = str(error)[:500]
    return fallback


def _succeeded(value):
    global last_error
    last_error = ''
    return value


def list_windows() -> list[tuple[int, str]]:
    global last_error
    try:
        with connection() as (client, root):
            handles = _property(client, root, '_NET_CLIENT_LIST_STACKING')
            if len(handles) > 4096:
                raise ValueError('Too many X11 windows')
            result = []
            for handle in handles:
                window = client.create_resource_object('window', int(handle))
                if window.get_attributes().map_state != 2:
                    continue
                value = _property(client, window, '_NET_WM_NAME')
                title = bytes(value).decode('utf-8', errors='replace') if len(value) else window.get_wm_name()
                if title:
                    result.append((int(handle), str(title)[:1000]))
            last_error = ''
            return result
    except Exception as error:
        return _failed(error, [])


def geometry(handle: int) -> tuple[int, int, int, int] | None:
    try:
        with connection() as (client, root):
            window = client.create_resource_object('window', int(handle))
            return _succeeded(_geometry(client, root, window))
    except Exception as error:
        return _failed(error, None)


def _send(client, root, handle: int, name: str, values: list[int]) -> None:
    from Xlib.protocol.event import ClientMessage
    if client.intern_atom(name) not in _property(client, root, '_NET_SUPPORTED'):
        raise ValueError('The X11 window manager does not support ' + name)
    window = client.create_resource_object('window', int(handle))
    window.get_attributes()  # Reject missing/reused handles before sending; bindings are never persisted.
    event = ClientMessage(window=window, client_type=client.intern_atom(name), data=(32, values))
    root.send_event(event, event_mask=(1 << 20) | (1 << 19))
    client.sync()


def move(handle: int, x: int, y: int, width: int, height: int) -> bool:
    try:
        with connection() as (client, root):
            # StaticGravity; x/y/width/height flags and pager source, in X11 physical coordinates.
            flags = 10 | (15 << 8) | (2 << 12)
            window = client.create_resource_object('window', int(handle))
            extent = _property(client, window, '_NET_FRAME_EXTENTS')
            left, right, top, bottom = extent[:4] if len(extent) == 4 else (0, 0, 0, 0)
            _send(client, root, handle, '_NET_MOVERESIZE_WINDOW',
                  [flags, int(x + left), int(y + top), max(40, int(width - left - right)),
                   max(40, int(height - top - bottom))])
            return _succeeded(True)
    except Exception as error:
        return _failed(error, False)


def pin(handle: int, enabled: bool) -> bool:
    try:
        with connection() as (client, root):
            _send(client, root, handle, '_NET_WM_STATE',
                  [1 if enabled else 0, client.intern_atom('_NET_WM_STATE_ABOVE'), 0, 2, 0])
            return _succeeded(True)
    except Exception as error:
        return _failed(error, False)


def opacity(handle: int, percent: int) -> bool:
    try:
        with connection() as (client, root):
            if not client.get_selection_owner(client.intern_atom('_NET_WM_CM_S0')):
                raise ValueError('X11 opacity requires a running compositing manager')
            window = client.create_resource_object('window', int(handle))
            window.change_property(client.intern_atom('_NET_WM_WINDOW_OPACITY'), client.intern_atom('CARDINAL'),
                                   32, [round(0xffffffff * max(20, min(100, percent)) / 100)])
            client.sync()
            return _succeeded(True)
    except Exception as error:
        return _failed(error, False)


def foreground() -> int | None:
    try:
        with connection() as (client, root):
            value = _property(client, root, '_NET_ACTIVE_WINDOW')
            return int(value[0]) if len(value) else None
    except Exception as error:
        return _failed(error, None)


def screen_rects() -> list[tuple[int, int, int, int]]:
    """Read physical XRandR monitor coordinates and intersect the EWMH work area."""
    try:
        from PySide6.QtCore import QRect
        with connection() as (client, root):
            monitors = root.xrandr_get_monitors(True).monitors
            if not 1 <= len(monitors) <= 16:
                raise ValueError('X11 monitor count unavailable or excessive')
            areas = _property(client, root, '_NET_WORKAREA')
            desktop = _property(client, root, '_NET_CURRENT_DESKTOP')
            index = int(desktop[0]) * 4 if len(desktop) else 0
            area = QRect(*map(int, areas[index:index + 4])) if len(areas) >= index + 4 else None
            result = []
            for monitor in monitors:
                rect = QRect(monitor.x, monitor.y, monitor.width_in_pixels, monitor.height_in_pixels)
                if area is not None:
                    rect = rect.intersected(area)
                if not rect.isEmpty():
                    result.append(rect.getRect())
            return _succeeded(result)
    except Exception as error:
        return _failed(error, [])
