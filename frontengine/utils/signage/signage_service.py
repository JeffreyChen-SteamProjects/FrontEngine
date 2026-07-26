"""
看板模式：依序輪播一組預設集，適合把機器擺著當展示螢幕。

輪播順序與時間是純邏輯（時鐘可注入），Qt 服務只負責定時問它「該換了嗎」。
啟動後主視窗可以收進系統匣，畫面上就只剩下覆蓋層本身。

Signage mode: rotate through a set of presets, for a machine left running as a
display.

The order and the timing are pure logic with an injectable clock; the Qt
service only asks it whether it is time yet. With it running the main window
can go to the tray, leaving nothing on screen but the overlays themselves.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from frontengine.utils.logging.loggin_instance import front_engine_logger

DEFAULT_INTERVAL_MINUTES = 5
MIN_INTERVAL_MINUTES = 1
MAX_INTERVAL_MINUTES = 24 * 60


def clamp_interval(value: Any, fallback: int = DEFAULT_INTERVAL_MINUTES) -> int:
    """輪播間隔夾在 1 分鐘到 24 小時。"""
    try:
        return max(MIN_INTERVAL_MINUTES, min(MAX_INTERVAL_MINUTES, int(float(value))))
    except (TypeError, ValueError):
        return fallback


def normalize_playlist(names: Any) -> List[str]:
    """
    整理輪播清單：去掉空白項目與重複，保持使用者排的順序。
    Tidy the rotation list: drop blanks and duplicates, keep the user's order.
    """
    if isinstance(names, str):
        raw = names.replace("\n", ",").split(",")
    elif isinstance(names, (list, tuple)):
        raw = names
    else:
        return []
    playlist: List[str] = []
    for item in raw:
        name = str(item or "").strip()
        if name and name not in playlist:
            playlist.append(name)
    return playlist


class SignageRotation:
    """
    輪播狀態：現在該顯示哪一個、什麼時候換下一個。純邏輯，時鐘可注入。
    Which preset is showing and when the next one is due. Pure logic with an
    injectable clock.
    """

    def __init__(self, config_provider: Callable[[], Dict[str, Any]],
                 now_provider: Callable[[], datetime] = datetime.now) -> None:
        self._config_provider = config_provider
        self._now = now_provider
        self.index = 0
        self._due: Optional[datetime] = None

    def playlist(self) -> List[str]:
        config = self._config_provider() or {}
        return normalize_playlist(config.get("presets"))

    def interval_minutes(self) -> int:
        config = self._config_provider() or {}
        return clamp_interval(config.get("interval_minutes"))

    def start(self) -> Optional[str]:
        """從頭開始輪播，回傳第一個要顯示的預設集（清單空的話是 None）。"""
        playlist = self.playlist()
        self.index = 0
        if not playlist:
            self._due = None
            return None
        self._due = self._now() + timedelta(minutes=self.interval_minutes())
        return playlist[0]

    def stop(self) -> None:
        self._due = None

    def seconds_left(self) -> float:
        """距離換下一個還有幾秒；沒在輪播就是 0。"""
        if self._due is None:
            return 0.0
        return max(0.0, (self._due - self._now()).total_seconds())

    def tick(self) -> Optional[str]:
        """
        時間到就前進到下一個並回傳它的名字，否則回傳 None。走到底會回到開頭。
        Advance and return the next preset when it is due, else None. It wraps
        at the end.
        """
        if self._due is None or self._now() < self._due:
            return None
        playlist = self.playlist()
        if not playlist:
            self._due = None
            return None
        self.index = (self.index + 1) % len(playlist)
        self._due = self._now() + timedelta(minutes=self.interval_minutes())
        return playlist[self.index]


class SignageService(QObject):
    """把輪播接上 QTimer，該換的時候發出預設集名稱。"""

    preset_due = Signal(str)

    def __init__(self, config_provider: Callable[[], Dict[str, Any]],
                 now_provider: Callable[[], datetime] = datetime.now,
                 interval_ms: int = 5000, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.rotation = SignageRotation(config_provider, now_provider)
        self._timer = QTimer(self)
        self._timer.setInterval(max(1000, int(interval_ms)))
        self._timer.timeout.connect(self.poll_once)

    @property
    def running(self) -> bool:
        return self._timer.isActive()

    def start(self) -> Optional[str]:
        """開始輪播並回傳第一個預設集。"""
        first = self.rotation.start()
        if first is None:
            front_engine_logger.info("[Signage] nothing to rotate")
            return None
        self._timer.start()
        front_engine_logger.info(f"[Signage] start | {first}")
        self.preset_due.emit(first)
        return first

    def stop(self) -> None:
        self._timer.stop()
        self.rotation.stop()
        front_engine_logger.info("[Signage] stop")

    def poll_once(self) -> None:
        """檢查一次是否該換（測試會直接呼叫）。"""
        try:
            following = self.rotation.tick()
        except Exception as error:  # pragma: no cover - defensive boundary
            front_engine_logger.warning(f"[Signage] tick error: {error!r}")
            return
        if following:
            front_engine_logger.info(f"[Signage] next | {following}")
            self.preset_due.emit(following)
