from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, QTimer, Signal

from frontengine.utils.logging.loggin_instance import front_engine_logger

# 預設的排程設定（預設停用）
# Default preset-schedule config (disabled by default).
# 星期用 0=週一 … 6=週日（和 datetime.weekday() 一致，省得多一層換算）。
# 空清單代表「每天」——沒有勾任何一天卻期待它每天觸發，比什麼都不做合理；
# 真的不想要就把整個排程關掉。
# Days are 0=Monday … 6=Sunday, matching datetime.weekday() so nothing has to be
# converted. An empty list means every day: someone who ticked no days but left
# the schedule on meant "every day" far more likely than "never" - and "never"
# is what switching the schedule off is for.
ALL_DAYS = (0, 1, 2, 3, 4, 5, 6)

DEFAULT_PRESET_SCHEDULE: Dict[str, Any] = {
    "enabled": False,
    "preset": "",
    "hour": 9,
    "minute": 0,
    "days": [],
}


def normalize_days(value: Any) -> List[int]:
    """
    把設定裡的星期整理成排序過、不重複、0..6 的清單。手動編過的設定檔可能塞進
    字串、負數或 99，這裡一律丟掉而不是讓排程在半夜炸掉。
    Tidy the configured days into a sorted, unique 0..6 list. A hand-edited
    settings file may hold strings, negatives or 99; those are dropped rather
    than left to break the schedule in the middle of the night.
    """
    if value is None:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple, set)):
        return []
    days = set()
    for item in value:
        try:
            day = int(item)
        except (TypeError, ValueError):
            continue
        if 0 <= day <= 6:
            days.add(day)
    return sorted(days)


def runs_today(config: Any, weekday: int) -> bool:
    """今天是不是該跑。沒有指定星期就是每天都跑。"""
    days = normalize_days((config or {}).get("days") if isinstance(config, dict) else None)
    return not days or weekday in days


def _coerce_int(value: Any, default: int, modulo: int) -> int:
    try:
        return int(value) % modulo
    except (TypeError, ValueError):
        return default


def _crossed(previous: datetime, now: datetime, target: int) -> bool:
    """
    上次輪詢到這次之間，有沒有經過 target 這一分鐘（午夜起算的分鐘數）。
    用完整的日期時間比：只看分鐘數的話，時鐘倒退（冬令時間、改時區）會被當成
    跨過午夜而在凌晨誤觸發。
    Whether the target minute lies between the previous poll and this one. Whole
    datetimes, not minutes of the day: by those a clock turned back - the end of
    daylight saving, a change of time zone - looked like midnight and fired.
    """
    moment = now.replace(hour=target // 60, minute=target % 60, second=0, microsecond=0)
    return previous < moment <= now


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
        self._previous: Optional[datetime] = None
        # Local date of the last firing per schedule (preset, minute of day). A clock
        # turned back - the end of daylight saving, a manual correction - crosses the
        # target minute a second time on the same date; this keeps that day to one run.
        self._last_fired: Dict[Tuple[str, int], date] = {}
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
                self._previous = None  # reset so re-enabling never instant-fires
                return
            preset = config.get("preset")
            if not isinstance(preset, str) or not preset.strip():
                return
            now = self._now_provider()
            target = _coerce_int(config.get("hour"), 9, 24) * 60 + _coerce_int(config.get("minute"), 0, 60)
            # 不該跑的日子仍要記下目前時間，否則隔天第一次輪詢會把「上次」當成
            # 未知而錯過當天的觸發點。
            # Days that do not run still record the current minute: otherwise the
            # first poll of the next day has no previous value and misses the
            # crossing entirely.
            if not runs_today(config, now.weekday()):
                self._previous = now
                return
        except Exception as error:  # pragma: no cover - defensive boundary
            front_engine_logger.warning(f"[PresetSchedule] poll error: {error!r}")
            return
        previous = self._previous
        self._previous = now
        if previous is not None and _crossed(previous, now, target):
            self._fire_once_per_day(preset.strip(), target, now.date())

    def _fire_once_per_day(self, preset: str, target: int, today: date) -> None:
        """Emit unless this schedule already fired on this local date."""
        schedule_id = (preset, target)
        if self._last_fired.get(schedule_id) == today:
            front_engine_logger.info(f"[PresetSchedule] already fired today | preset={preset}")
            return
        # Only today's records can still suppress anything; older ones are dropped.
        self._last_fired = {key: day for key, day in self._last_fired.items() if day == today}
        self._last_fired[schedule_id] = today
        front_engine_logger.info(f"[PresetSchedule] fire | preset={preset}")
        self.preset_due.emit(preset)

    def poll_once(self) -> None:
        """Run a single poll immediately (used by tests)."""
        self._poll()
