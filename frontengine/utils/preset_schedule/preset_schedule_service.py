from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from frontengine.utils.logging.loggin_instance import front_engine_logger

# 預設的排程設定（預設停用）
# Default preset-schedule config (disabled by default).
DEFAULT_PRESET_SCHEDULE: Dict[str, Any] = {
    "enabled": False,
    "preset": "",
    "hour": 9,
    "minute": 0,
}


def _coerce_int(value: Any, default: int, modulo: int) -> int:
    try:
        return int(value) % modulo
    except (TypeError, ValueError):
        return default


def _crossed(previous: int, target: int, current: int) -> bool:
    """
    上次輪詢到這次之間，有沒有經過 target 這一分鐘（全部以「午夜起算的分鐘數」表示）。
    午夜會讓分鐘數從 1439 掉回 0，直接寫 previous < target <= current 的話，
    排在 00:00 的預設集永遠等不到——沒有哪個 previous 會小於 0。
    Whether the target minute was passed between the previous poll and this one,
    all counted as minutes since midnight. Midnight drops the count from 1439
    back to 0, so a plain `previous < target <= current` can never be satisfied
    for a preset scheduled at 00:00: no previous value is below zero.
    """
    if previous <= current:
        return previous < target <= current
    return target > previous or target <= current


class PresetScheduleService(QObject):
    """
    每天在指定時間套用一個預設集。以「跨越目標時間」偵測觸發，因此每天只會
    觸發一次，且程式啟動時若已過該時間也不會立刻誤觸發。時鐘與設定可注入。
    Apply a preset at a configured time each day. Fires on the crossing from
    before to at/after the target minute, so it triggers once per day and does
    not fire at startup if the time has already passed. Clock/config injectable.
    """

    preset_due = Signal(str)

    def __init__(
        self,
        config_provider: Callable[[], Dict[str, Any]],
        now_provider: Optional[Callable[[], datetime]] = None,
        interval_ms: int = 30000,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._config_provider = config_provider
        self._now_provider = now_provider or datetime.now
        self._prev_minutes: Optional[int] = None
        self._timer = QTimer(self)
        self._timer.setInterval(max(1000, int(interval_ms)))
        self._timer.timeout.connect(self._poll)

    def start(self) -> None:
        front_engine_logger.info("[PresetSchedule] start")
        self._timer.start()
        self._poll()

    def stop(self) -> None:
        front_engine_logger.info("[PresetSchedule] stop")
        self._timer.stop()

    def _poll(self) -> None:
        try:
            config = self._config_provider() or {}
            if not config.get("enabled"):
                self._prev_minutes = None  # reset so re-enabling never instant-fires
                return
            preset = config.get("preset")
            if not isinstance(preset, str) or not preset.strip():
                return
            now = self._now_provider()
            target = _coerce_int(config.get("hour"), 9, 24) * 60 + _coerce_int(config.get("minute"), 0, 60)
            current = now.hour * 60 + now.minute
        except Exception as error:  # pragma: no cover - defensive boundary
            front_engine_logger.warning(f"[PresetSchedule] poll error: {error!r}")
            return
        previous = self._prev_minutes
        self._prev_minutes = current
        if previous is not None and _crossed(previous, target, current):
            front_engine_logger.info(f"[PresetSchedule] fire | preset={preset}")
            self.preset_due.emit(preset.strip())

    def poll_once(self) -> None:
        """Run a single poll immediately (used by tests)."""
        self._poll()
