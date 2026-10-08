"""Do not describe Xwayland-only input as desktop-wide Wayland support."""
from __future__ import annotations
import os
import sys
from pathlib import Path


def x11_reason(*, platform: str | None = None, environment: dict | None = None) -> str:
    """Empty means an X11 session exists; operations still require a cooperating WM."""
    platform, env = platform or sys.platform, os.environ if environment is None else environment
    if not platform.startswith('linux'):
        return 'This adapter requires Linux.'
    if (env.get('WAYLAND_DISPLAY') or env.get('XDG_SESSION_TYPE', '').lower() == 'wayland'
            or env.get('QT_QPA_PLATFORM', '').startswith('wayland')):
        return 'Wayland: arbitrary-window control and desktop-wide pynput input are unavailable; Xwayland covers only its own clients.'
    if not env.get('DISPLAY'):
        return 'X11 DISPLAY is missing; use a desktop X11 session.'
    return ''


def parec_path() -> str | None:
    """Only distro-owned fixed absolute paths, never a command from PATH."""
    return next((path for path in ('/usr/bin/parec', '/bin/parec') if Path(path).is_file()), None)


def audio_reason() -> str:
    """Server/device permissions are checked only on explicit capture startup."""
    if not sys.platform.startswith('linux'):
        return 'This adapter requires Linux.'
    if parec_path() is None:
        return 'Install pulseaudio-utils (parec), with PulseAudio or PipeWire Pulse compatibility running.'
    return ''
