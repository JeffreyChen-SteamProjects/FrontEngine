"""
媒體播放控制：送出系統的媒體按鍵（播放/暫停、下一首、上一首）。

「正在播放」小工具看得到曲目卻碰不到它，這裡補上那一半。做法是送出鍵盤上本來
就有的媒體鍵虛擬碼，走 ctypes 的 `keybd_event`——**不需要 WinRT 投影套件**，
也就是說它繞開了擋住 SMTC 曲名的那道牆。

**做得到什麼、做不到什麼**：媒體鍵是廣播給前景／註冊過的播放器的，所以只對
「認得媒體鍵」的程式有效（Spotify、瀏覽器、大部分播放器可以；有些老程式不行）。
送出去之後沒有任何回報，因此 `send_media_key()` 回傳的是「有沒有成功送出」，
不是「播放器有沒有照做」——把它當成執行結果會是騙人的。

Media transport control: send the system media keys (play/pause, next,
previous).

The "now playing" widget can see the track but not touch it; this is the other
half. It sends the media-key virtual codes a keyboard already has, through
ctypes `keybd_event` - **no WinRT projection package needed**, so it steps
around the wall that blocks the SMTC track name.

**What it can and cannot do**: media keys are broadcast to the foreground or
registered player, so they only reach applications that are media-key aware
(Spotify, browsers and most players are; some older ones are not). Nothing is
reported back, so `send_media_key()` returns whether the key was *sent*, not
whether a player acted on it - treating it as the outcome would be a lie.

實機量過（Windows 11，2026-08）：對正在播放的 Microsoft Edge 送一次
播放/暫停，WASAPI 的出聲工作階段確實消失，再送一次又回來——鍵真的到得了播放器。
Measured on real hardware (Windows 11, Aug 2026): one play/pause against a
playing Microsoft Edge made the audible WASAPI session disappear, and a second
press brought it back - the key does reach a real player.
"""
from __future__ import annotations

import sys
from typing import Dict, Optional, Tuple

from frontengine.utils.logging.loggin_instance import front_engine_logger

# Win32 虛擬鍵碼 / Win32 virtual key codes
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

# 動作名稱沿用主視窗既有的快速鍵動作命名，這樣快速鍵、手機遙控與 MIDI
# 三條路都不必各自認識媒體控制。
# The action names follow the main window's existing hotkey actions, so
# hotkeys, the phone remote and MIDI all reach these without special cases.
ACTION_PLAY_PAUSE = "media_play_pause"
ACTION_NEXT = "media_next"
ACTION_PREVIOUS = "media_previous"
ACTION_STOP = "media_stop"
ACTIONS: Tuple[str, ...] = (ACTION_PLAY_PAUSE, ACTION_NEXT, ACTION_PREVIOUS, ACTION_STOP)

_KEY_CODES: Dict[str, int] = {
    ACTION_PLAY_PAUSE: VK_MEDIA_PLAY_PAUSE,
    ACTION_NEXT: VK_MEDIA_NEXT_TRACK,
    ACTION_PREVIOUS: VK_MEDIA_PREV_TRACK,
    ACTION_STOP: VK_MEDIA_STOP,
}


def available() -> bool:
    """
    這個平台能不能送媒體鍵。keybd_event 是 Win32 的，其他平台上沒有等價的
    「廣播給播放器」機制可以照抄。
    Whether media keys can be sent here. keybd_event is Win32; other platforms
    have no equivalent broadcast-to-the-player call to copy.
    """
    return sys.platform == "win32"


def is_media_action(action) -> bool:
    """這個動作名稱是不是媒體控制。"""
    return action in _KEY_CODES


def key_code(action) -> Optional[int]:
    """動作對應的虛擬鍵碼；不是媒體動作回傳 None。"""
    return _KEY_CODES.get(action)


def _default_sender():
    """
    取得宣告好 argtypes 的 keybd_event。非 Windows 或載不到時擲出 OSError，
    由呼叫端決定怎麼降級。
    The keybd_event entry point with its argtypes declared. Raises OSError off
    Windows or when it cannot be loaded, and the caller decides how to degrade.
    """
    if not available():
        raise OSError("media keys are Windows only")
    import ctypes

    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        user32.keybd_event.argtypes = [
            ctypes.c_ubyte, ctypes.c_ubyte, ctypes.c_uint, ctypes.c_void_p,
        ]
        user32.keybd_event.restype = None
        return user32.keybd_event
    except (AttributeError, OSError) as error:  # pragma: no cover - Windows only
        raise OSError(f"keybd_event unavailable: {error!r}") from error


def send_media_key(action, sender=None) -> bool:
    """
    送出一個媒體鍵；回傳是否成功送出（不是播放器是否照做，見模組說明）。
    `sender` 可注入以便測試，簽章與 keybd_event 相同。
    Send one media key. Returns whether it was sent - not whether a player
    acted on it, see the module docstring. `sender` is injectable for tests and
    takes keybd_event's own signature.
    """
    code = key_code(action)
    if code is None:
        return False
    if sender is None:
        try:
            sender = _default_sender()
        except OSError as error:
            front_engine_logger.info(f"[media_keys] not sending {action}: {error}")
            return False
    try:
        # 按下與放開都要送。只送按下的話，某些播放器會當成鍵一直被按著。
        # Both halves are sent: with the key never released, some players treat
        # it as held down.
        sender(code, 0, KEYEVENTF_EXTENDEDKEY, None)
        sender(code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, None)
    except Exception as error:  # pragma: no cover - defensive around the native call
        front_engine_logger.warning(f"[media_keys] {action} failed: {error!r}")
        return False
    front_engine_logger.info(f"[media_keys] sent {action}")
    return True
