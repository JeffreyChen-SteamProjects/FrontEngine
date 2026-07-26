"""
使用時間統計服務：定時看一次前景程式，交給 UsageTracker 累積。使用者閒置
（沒碰鍵盤滑鼠）時會暫停，不然離開座位也會被算成「在用某個程式」。

只有使用者明確開啟才會啟動；關掉時立刻停止並把目前的統計寫回本機檔案。

The usage-tracking service: sample the foreground app on a timer and let
UsageTracker accumulate it. It pauses while the user is idle, so stepping away
is not billed to whatever was left in front.

It only runs when the user turns it on, and stops - flushing to the local file -
the moment they turn it off.
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.platform_info.platform_info import active_app_name, idle_seconds
from frontengine.utils.usage_tracking.usage_tracker import UsageTracker

DEFAULT_INTERVAL_MS = 15000
# 閒置超過這麼久就不算在使用中
# Idle for longer than this stops counting.
IDLE_CUTOFF_SECONDS = 90


class UsageTrackingService(QObject):
    """把 UsageTracker 接上 QTimer；程式來源與閒置來源都可注入。"""

    sampled = Signal(str)

    def __init__(self, tracker: UsageTracker,
                 app_provider: Optional[Callable[[], Optional[str]]] = None,
                 idle_provider: Optional[Callable[[], Optional[float]]] = None,
                 interval_ms: int = DEFAULT_INTERVAL_MS,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.tracker = tracker
        self._app_provider = app_provider or active_app_name
        self._idle_provider = idle_provider or idle_seconds
        self._timer = QTimer(self)
        self._timer.setInterval(max(1000, int(interval_ms)))
        self._timer.timeout.connect(self.poll_once)

    @property
    def running(self) -> bool:
        return self._timer.isActive()

    def start(self) -> None:
        front_engine_logger.info("[UsageTracking] start")
        self.tracker.load()
        self.tracker.pause()
        self._timer.start()

    def stop(self) -> None:
        """
        停止並把統計寫回本機檔案。沒有任何紀錄時 save() 不會建立檔案，所以
        「一直關著」的使用者磁碟上不會多出東西。
        Stop and flush to the local file. With nothing recorded save() creates
        no file, so a user who leaves this off never gains one.
        """
        front_engine_logger.info("[UsageTracking] stop")
        self._timer.stop()
        self.tracker.pause()
        self.tracker.save()

    def poll_once(self) -> None:
        """取樣一次（測試會直接呼叫）。"""
        try:
            idle = self._idle_provider()
            if idle is not None and idle >= IDLE_CUTOFF_SECONDS:
                self.tracker.pause()
                return
            app = self._app_provider()
        except Exception as error:  # pragma: no cover - defensive boundary
            front_engine_logger.warning(f"[UsageTracking] poll error: {error!r}")
            return
        if not app:
            self.tracker.pause()
            return
        self.tracker.observe(app)
        self.sampled.emit(str(app))
