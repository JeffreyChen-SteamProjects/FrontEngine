from .backend import get_backend

_MEDIA_CODES = {'media_play_pause': 16, 'media_next': 17, 'media_previous': 18}
_FUNCTION_CODES = (122, 120, 99, 118, 96, 97, 98, 100, 101, 109, 103, 111,
                   105, 107, 113, 106, 64, 79, 80, 90)
_LETTER_CODES = dict(zip('ASDFHGZXCVBQWERYT123465=97-80]OUIP[LJ\'K;\\,/NM.',
                         range(48)))


def send_media_key(action: str, backend=None) -> bool:
    backend = backend or get_backend()
    code = _MEDIA_CODES.get(action)
    state = backend.capability('media_keys')
    if code is None or not state.available:
        backend.last_error = state.reason or 'macOS has no supported stop media-key code'
        return False
    try:
        appkit = backend.framework('AppKit')
        quartz = backend.framework('Quartz')
        for key_state in (0xA, 0xB):
            event = appkit.NSEvent.otherEventWithType_location_modifierFlags_timestamp_windowNumber_context_subtype_data1_data2_(
                appkit.NSSystemDefined, (0, 0), 0, 0, 0, None, 8,
                (code << 16) | (key_state << 8), -1)
            if event is None or event.CGEvent() is None:
                return False
            quartz.CGEventPost(quartz.kCGHIDEventTap, event.CGEvent())
        return True
    except (ImportError, AttributeError, OSError) as error:
        backend.last_error = str(error)
        return False


def key_is_pressed(virtual_key, backend=None) -> bool:
    backend = backend or get_backend()
    if isinstance(virtual_key, str) and len(virtual_key) == 1:
        virtual_key = ord(virtual_key.upper())
    if not isinstance(virtual_key, int):
        raise ValueError('keycode must be an integer or a single character')
    if 0x70 <= virtual_key < 0x70 + len(_FUNCTION_CODES):
        code = _FUNCTION_CODES[virtual_key - 0x70]
    else:
        code = _LETTER_CODES.get(chr(virtual_key))
    if code is None:
        return False
    quartz = backend.framework('Quartz')
    return bool(quartz.CGEventSourceKeyState(quartz.kCGEventSourceStateCombinedSessionState, code))
