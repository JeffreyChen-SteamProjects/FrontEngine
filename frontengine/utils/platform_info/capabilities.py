"""Runtime prerequisites and precise adapter failures, without starting capture or listeners."""
from __future__ import annotations
import sys


def platform_capabilities() -> list[tuple[str, bool, str]]:
    """Availability means adapter prerequisites, never a replacement for native acceptance."""
    if sys.platform.startswith('linux'):
        return _linux_rows()
    if sys.platform == 'darwin':
        from frontengine.utils.macos import get_backend
        return [(name, value.available, value.reason) for name in
                ('screen_capture', 'system_audio', 'microphone', 'window_move', 'global_hotkey', 'midi')
                for value in [get_backend().capability(name)]]
    if sys.platform == 'win32':
        return [('system_audio', True, 'WASAPI adapter; audio device checked when opened.'),
                ('microphone', True, 'WASAPI meter; input device checked when opened.'),
                ('window_move', True, 'Win32 adapter; target access can be denied by UIPI.'),
                ('global_hotkey', True, 'pynput Windows adapter; listener startup may still fail.')]
    return [('platform', False, 'No native adapter for this platform.')]


def _linux_rows() -> list[tuple[str, bool, str]]:
    from frontengine.utils.linux.capabilities import x11_reason, audio_reason
    from frontengine.utils.linux import windows
    from frontengine.utils.linux.audio import errors
    from frontengine.utils.input_watch.input_watch_service import InputWatchService, _PYNPUT_ERROR
    session_reason, sound_reason = x11_reason(), audio_reason()
    input_reason = session_reason
    if not input_reason and not InputWatchService.available():
        input_reason = 'pynput input backend unavailable: ' + str(_PYNPUT_ERROR)[:500]
    sound_failures = errors()
    if sound_failures:
        sound_reason = '; '.join(sound_failures)
    window_reason = session_reason or windows.last_error
    if not window_reason and not windows.available():
        window_reason = 'Install python-xlib; an EWMH-compliant X11 window manager is required.'
    return [('system_audio', not sound_reason, sound_reason or 'parec installed; server/device checked on opt-in. Audio samples stay in memory.'),
            ('microphone', not sound_reason, sound_reason or 'Lazy parec default source; starts on first enabled meter sample.'),
            ('window_move', not window_reason, window_reason or 'X11 EWMH requests; compositing manager required for opacity.'),
            ('global_hotkey', not input_reason, input_reason or 'X11 pynput; DISPLAY and server permissions required.'),
            ('multi_monitor', not session_reason, session_reason or 'Qt logical profile movement; mixed-DPI hardware acceptance is still pending.')]
