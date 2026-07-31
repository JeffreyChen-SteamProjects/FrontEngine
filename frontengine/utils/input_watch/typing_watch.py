"""
「使用者正在打字嗎」——用來讓桌寵在打字時安分下來。

桌寵在螢幕上到處跑，是打字時最常被抱怨的一點：牠正好跑過你在看的那一行。這裡只
記住最後一次按鍵的時間，讓呼叫端問「現在算不算在打字」。

時鐘可以注入，所以測試不必真的等兩秒。

"Is the user typing?" - so the desktop pet can settle down while they are.

A pet wandering across the screen is the thing people complain about most while
typing: it walks over the line you are reading. This only remembers when the last
key went down and lets the caller ask whether that counts as typing now.

The clock is injectable, so tests do not wait two seconds.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Optional

DEFAULT_SETTLE_SECONDS = 2.0
MIN_SETTLE_SECONDS = 0.5
MAX_SETTLE_SECONDS = 30.0


def clamp_settle_seconds(value: Any, fallback: float = DEFAULT_SETTLE_SECONDS) -> float:
    """安分的持續時間夾在 0.5 到 30 秒。"""
    try:
        return max(MIN_SETTLE_SECONDS, min(MAX_SETTLE_SECONDS, float(value)))
    except (TypeError, ValueError):
        return fallback


class TypingWatch:
    """
    記住最後一次按鍵的時間，回答「現在還算在打字嗎」。

    用單調時鐘而不是牆上時鐘：系統時間被調整（校時、換時區）時，牆上時鐘會讓
    「距離上次按鍵幾秒」變成負數或一大跳，寵物就會莫名其妙卡住或突然衝出去。
    Remembers when the last key went down and answers whether that still counts
    as typing.

    On a monotonic clock rather than the wall clock: when the system time is
    adjusted - an NTP step, a timezone change - a wall clock makes "seconds since
    the last key" negative or wildly large, and the pet either freezes for no
    reason or bolts.
    """

    def __init__(self, settle_seconds: Any = DEFAULT_SETTLE_SECONDS,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.settle_seconds = clamp_settle_seconds(settle_seconds)
        self._clock = clock
        self._last_key: Optional[float] = None

    def note_key(self) -> None:
        """記下這一刻有人按了鍵。"""
        self._last_key = self._clock()

    def clear(self) -> None:
        """忘掉先前的按鍵（功能關掉時用，免得寵物停在原地不動）。"""
        self._last_key = None

    def seconds_since_key(self) -> Optional[float]:
        """距離上次按鍵幾秒；還沒按過就是 None。"""
        if self._last_key is None:
            return None
        return max(0.0, self._clock() - self._last_key)

    def typing(self) -> bool:
        """現在算不算在打字。"""
        elapsed = self.seconds_since_key()
        return elapsed is not None and elapsed < self.settle_seconds
