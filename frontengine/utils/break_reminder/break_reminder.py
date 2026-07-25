"""
護眼休息提醒（20-20-20 法則）：每工作一段時間，提醒把視線移開 20 秒。
純狀態機、不依賴 Qt，時間由注入的 now_provider 提供，方便測試。

Eye-break reminders built on the 20-20-20 rule: after a stretch of work, look
away for twenty seconds. A pure, Qt-free state machine whose clock is injected.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Optional

PHASE_IDLE = "idle"
PHASE_WORK = "work"
PHASE_REST = "rest"

# 20-20-20：每 20 分鐘，看 20 英尺外 20 秒
# 20-20-20: every 20 minutes, look 20 feet away for 20 seconds.
DEFAULT_WORK_MINUTES = 20
DEFAULT_REST_SECONDS = 20


def clamp_minutes(value, fallback: int = DEFAULT_WORK_MINUTES) -> int:
    """把工作區間夾在 1~180 分鐘。"""
    try:
        return max(1, min(180, int(float(value))))
    except (TypeError, ValueError):
        return fallback


def clamp_seconds(value, fallback: int = DEFAULT_REST_SECONDS) -> int:
    """把休息長度夾在 5~600 秒。"""
    try:
        return max(5, min(600, int(float(value))))
    except (TypeError, ValueError):
        return fallback


class BreakReminder:
    """
    休息提醒：start() 後進入工作階段，tick() 在時間到時切換到休息／回到工作，
    並回傳新的階段（沒換階段回傳 None），呼叫端據此顯示或收起提示畫面。
    """

    def __init__(self, work_minutes: int = DEFAULT_WORK_MINUTES,
                 rest_seconds: int = DEFAULT_REST_SECONDS,
                 now_provider: Callable[[], datetime] = datetime.now) -> None:
        self.work_minutes = clamp_minutes(work_minutes)
        self.rest_seconds = clamp_seconds(rest_seconds)
        self._now = now_provider
        self.phase = PHASE_IDLE
        self.completed_breaks = 0
        self._phase_ends: Optional[datetime] = None

    @property
    def running(self) -> bool:
        return self.phase != PHASE_IDLE

    def start(self) -> str:
        """開始一輪工作 / Begin a work stretch."""
        self.completed_breaks = 0
        self._enter(PHASE_WORK)
        return self.phase

    def stop(self) -> None:
        """停止提醒 / Stop reminding."""
        self.phase = PHASE_IDLE
        self._phase_ends = None

    def snooze(self, minutes: int = 5) -> None:
        """晚點再說：把目前階段往後延（休息中則直接回到工作）。"""
        self._enter(PHASE_WORK)
        self._phase_ends = self._now() + timedelta(minutes=clamp_minutes(minutes, 5))

    def _enter(self, phase: str) -> None:
        self.phase = phase
        if phase == PHASE_WORK:
            self._phase_ends = self._now() + timedelta(minutes=self.work_minutes)
        elif phase == PHASE_REST:
            self._phase_ends = self._now() + timedelta(seconds=self.rest_seconds)
        else:
            self._phase_ends = None

    def remaining_seconds(self) -> float:
        """本階段剩餘秒數；閒置時為 0。"""
        if self._phase_ends is None:
            return 0.0
        return max(0.0, (self._phase_ends - self._now()).total_seconds())

    def tick(self) -> Optional[str]:
        """
        推進計時：時間未到回傳 None；工作結束回傳 rest，休息結束回傳 work。
        Advance the timer, returning the new phase when one just ended.
        """
        if not self.running or self._phase_ends is None:
            return None
        if self._now() < self._phase_ends:
            return None
        if self.phase == PHASE_WORK:
            self._enter(PHASE_REST)
        else:
            self.completed_breaks += 1
            self._enter(PHASE_WORK)
        return self.phase
