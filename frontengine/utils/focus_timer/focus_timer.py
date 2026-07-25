"""
番茄鐘／專注計時的純狀態機：專注 -> 休息 -> 專注…，每完成幾輪給一次長休息。
時間由注入的 now_provider 提供，因此完全可測試、不依賴 Qt。

A pure focus-timer (pomodoro) state machine: focus -> break -> focus…, with a
long break every few rounds. Time comes from an injected `now_provider`, so it
is fully testable and Qt-free.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Optional

PHASE_IDLE = "idle"
PHASE_FOCUS = "focus"
PHASE_BREAK = "break"
PHASE_LONG_BREAK = "long_break"

PHASES = (PHASE_IDLE, PHASE_FOCUS, PHASE_BREAK, PHASE_LONG_BREAK)


def clamp_minutes(value, fallback: int, minimum: int = 1, maximum: int = 180) -> int:
    """把分鐘數夾到合理範圍；無法解析時用 fallback。"""
    try:
        return max(minimum, min(maximum, int(float(value))))
    except (TypeError, ValueError):
        return fallback


class FocusTimer:
    """
    專注計時器：start() 進入專注，tick() 在時間到時自動換到下一個階段並回傳新階段
    （沒換階段回傳 None）。完成 rounds 輪專注後給一次長休息。

    Focus timer: start() begins a focus phase; tick() advances to the next phase
    when the current one runs out and returns the new phase (None when nothing
    changed). A long break follows every `rounds` focus phases.
    """

    def __init__(self, focus_minutes: int = 25, break_minutes: int = 5,
                 long_break_minutes: int = 15, rounds: int = 4,
                 now_provider: Callable[[], datetime] = datetime.now) -> None:
        self.focus_minutes = clamp_minutes(focus_minutes, 25)
        self.break_minutes = clamp_minutes(break_minutes, 5)
        self.long_break_minutes = clamp_minutes(long_break_minutes, 15)
        try:
            self.rounds = max(1, int(rounds))
        except (TypeError, ValueError):
            self.rounds = 4
        self._now = now_provider
        self.phase = PHASE_IDLE
        self.completed_focus = 0
        self._phase_ends: Optional[datetime] = None

    @property
    def running(self) -> bool:
        return self.phase != PHASE_IDLE

    def phase_minutes(self, phase: str) -> int:
        """該階段的長度（分鐘）。"""
        if phase == PHASE_FOCUS:
            return self.focus_minutes
        if phase == PHASE_BREAK:
            return self.break_minutes
        if phase == PHASE_LONG_BREAK:
            return self.long_break_minutes
        return 0

    def start(self) -> str:
        """開始一次專注（重設輪數）/ Begin a focus phase, resetting the round count."""
        self.completed_focus = 0
        self._enter(PHASE_FOCUS)
        return self.phase

    def stop(self) -> None:
        """停止計時，回到閒置 / Stop and go back to idle."""
        self.phase = PHASE_IDLE
        self._phase_ends = None

    def _enter(self, phase: str) -> None:
        self.phase = phase
        minutes = self.phase_minutes(phase)
        self._phase_ends = self._now() + timedelta(minutes=minutes) if minutes else None

    def remaining_seconds(self) -> float:
        """本階段剩餘秒數；閒置時為 0。"""
        if self._phase_ends is None:
            return 0.0
        return max(0.0, (self._phase_ends - self._now()).total_seconds())

    def next_phase(self) -> str:
        """算出目前階段結束後應該進入哪個階段（不改變狀態）。"""
        if self.phase != PHASE_FOCUS:
            return PHASE_FOCUS
        if (self.completed_focus + 1) % self.rounds == 0:
            return PHASE_LONG_BREAK
        return PHASE_BREAK

    def tick(self) -> Optional[str]:
        """
        推進計時：時間未到回傳 None，時間到則切換到下一階段並回傳其名稱。
        Advance the timer, returning the new phase when one just ended.
        """
        if not self.running or self._phase_ends is None:
            return None
        if self._now() < self._phase_ends:
            return None
        upcoming = self.next_phase()
        if self.phase == PHASE_FOCUS:
            self.completed_focus += 1
        self._enter(upcoming)
        return upcoming
