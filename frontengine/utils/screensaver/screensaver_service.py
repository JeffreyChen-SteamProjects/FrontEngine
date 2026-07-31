"""
螢幕保護模式：閒置到一定時間就把選定的覆蓋層放上來，人回來就收掉。

這個程式的介紹一直寫著「or only use like screen saver」，但真正讓它自己啟動的
那一段從來沒有寫。閒置秒數在 `platform_info.idle_seconds()` 裡早就有了（Windows、
macOS、X11 三種都有），只是沒有任何地方在用。

閒置判斷是純邏輯，時間來源可以注入，所以測試不必真的等五分鐘也不必去動滑鼠。
Qt 服務只負責定時問它「狀態變了嗎」。

Screensaver mode: put the chosen overlay on screen once the machine has been
idle long enough, and take it away when someone comes back.

The application has always described itself as "or only use like screen saver",
but the part that starts it on its own was never written. The idle seconds were
already there in `platform_info.idle_seconds()` - Windows, macOS and X11 - with
nothing reading them.

The idle decision is pure logic with an injectable clock, so a test does not have
to wait five minutes or move a mouse. The Qt service only asks it, on a timer,
whether the state changed.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.platform_info.platform_info import idle_seconds

DEFAULT_IDLE_MINUTES = 5
MIN_IDLE_MINUTES = 1
MAX_IDLE_MINUTES = 24 * 60

# 可以當螢幕保護內容的分頁。順序就是設定畫面下拉選單的順序。
# The pages that can be the screensaver. This order is the order in the dialog.
SOURCES = ("video", "image", "gif", "particle", "web")
DEFAULT_SOURCE = "video"

DEFAULT_SCREENSAVER: Dict[str, Any] = {
    "enabled": False,
    "idle_minutes": DEFAULT_IDLE_MINUTES,
    "source": DEFAULT_SOURCE,
}


def clamp_idle_minutes(value: Any, fallback: int = DEFAULT_IDLE_MINUTES) -> int:
    """閒置門檻夾在 1 分鐘到 24 小時之間。"""
    try:
        return max(MIN_IDLE_MINUTES, min(MAX_IDLE_MINUTES, int(float(value))))
    except (TypeError, ValueError):
        return fallback


def normalize_source(value: Any, fallback: str = DEFAULT_SOURCE) -> str:
    """把設定裡的來源名稱正規化；不認得的就用預設。"""
    name = str(value or "").strip().lower()
    return name if name in SOURCES else fallback


class ScreensaverState:
    """
    依閒置秒數決定該開還是該關。純邏輯，閒置秒數可以注入。

    只在「狀態真的改變」時回話，所以呼叫端不必自己記上一次是什麼——每次輪詢都
    回報「該開了」會把覆蓋層重開一遍又一遍。

    Decides from the idle seconds whether it should be on or off, as pure logic
    with an injectable idle source.

    It speaks only when the state actually changes, so the caller does not have
    to remember the last answer: reporting "should be on" on every poll would
    reopen the overlay over and over.
    """

    def __init__(self, config_provider: Callable[[], Dict[str, Any]],
                 idle_provider: Callable[[], Optional[float]] = idle_seconds) -> None:
        self._config_provider = config_provider
        self._idle = idle_provider
        self.active = False

    def _config(self) -> Dict[str, Any]:
        config = self._config_provider() or {}
        return config if isinstance(config, dict) else {}

    def enabled(self) -> bool:
        return bool(self._config().get("enabled"))

    def idle_minutes(self) -> int:
        return clamp_idle_minutes(self._config().get("idle_minutes"))

    def source(self) -> str:
        return normalize_source(self._config().get("source"))

    def poll(self) -> Optional[bool]:
        """
        回傳 True 表示「現在該開」、False 表示「現在該關」、None 表示沒有變化。

        關掉的條件不只是「人回來了」：功能被關掉時也要收乾淨，否則使用者關掉開關
        之後畫面上還留著一層自己不會消失的覆蓋層。

        True to start now, False to stop now, None when nothing changed.

        Stopping is not only about someone coming back: switching the feature off
        has to clear the screen too, or the user is left with an overlay that
        will not go away on its own.
        """
        if not self.enabled():
            if self.active:
                self.active = False
                return False
            return None

        seconds = self._idle()
        if seconds is None:
            # 這個平台問不到閒置時間，就不要自作主張把東西放上螢幕。
            # No idle reading on this platform: do not put things on screen by guess.
            if self.active:
                self.active = False
                return False
            return None

        should_be_active = seconds >= self.idle_minutes() * 60
        if should_be_active == self.active:
            return None
        self.active = should_be_active
        return should_be_active


class ScreensaverService(QObject):
    """把閒置判斷接上 QTimer，狀態改變時發出訊號。"""

    screensaver_started = Signal(str)   # 要顯示哪一個來源 / which source to show
    screensaver_stopped = Signal()

    def __init__(self, config_provider: Callable[[], Dict[str, Any]],
                 idle_provider: Callable[[], Optional[float]] = idle_seconds,
                 interval_ms: int = 5000, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.state = ScreensaverState(config_provider, idle_provider)
        self._timer = QTimer(self)
        self._timer.setInterval(max(1000, int(interval_ms)))
        self._timer.timeout.connect(self.poll_once)

    @property
    def running(self) -> bool:
        return self._timer.isActive()

    @property
    def active(self) -> bool:
        return self.state.active

    def start(self) -> None:
        self._timer.start()
        front_engine_logger.info("[Screensaver] start")

    def stop(self) -> None:
        self._timer.stop()
        front_engine_logger.info("[Screensaver] stop")

    def poll_once(self) -> None:
        """檢查一次閒置狀態（測試直接呼叫這個，不必等計時器）。"""
        try:
            change = self.state.poll()
        except Exception as error:  # pragma: no cover - defensive boundary
            front_engine_logger.warning(f"[Screensaver] poll error: {error!r}")
            return
        if change is None:
            return
        if change:
            source = self.state.source()
            front_engine_logger.info(f"[Screensaver] idle, showing {source}")
            self.screensaver_started.emit(source)
        else:
            front_engine_logger.info("[Screensaver] back, clearing")
            self.screensaver_stopped.emit()
