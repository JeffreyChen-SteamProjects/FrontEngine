"""
自訂提醒：可以每隔一段時間提醒一次（喝水、起來走走），也可以每天在固定
時間提醒一次（會議、吃藥）。判斷邏輯是純狀態機、時鐘可注入，Qt 服務只負責
定時呼叫它並把到期的提醒發出去。

Custom reminders: either every N minutes (drink water, stand up) or once a day
at a set time (a meeting, a pill). The decision logic is a pure state machine
with an injectable clock; the Qt service just ticks it and emits what came due.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from frontengine.utils.logging.loggin_instance import front_engine_logger

KIND_EVERY = "every"
KIND_AT = "at"

MIN_EVERY_MINUTES = 1
MAX_EVERY_MINUTES = 24 * 60
DEFAULT_EVERY_MINUTES = 45


def clamp_every_minutes(value: Any, fallback: int = DEFAULT_EVERY_MINUTES) -> int:
    """把間隔夾在 1 分鐘到 24 小時之間。"""
    try:
        return max(MIN_EVERY_MINUTES, min(MAX_EVERY_MINUTES, int(float(value))))
    except (TypeError, ValueError):
        return fallback


def parse_time_of_day(text: Any) -> Optional[tuple]:
    """
    把 "14:30" 這種字串解析成 (時, 分)；格式不對回傳 None。
    Parse "14:30" into (hour, minute), or None when it is not a valid time.
    """
    if text is None:
        return None
    parts = str(text).strip().split(":")
    if len(parts) != 2:
        return None
    try:
        hour, minute = int(parts[0]), int(parts[1])
    except (TypeError, ValueError):
        return None
    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return (hour, minute)
    return None


def normalize_reminder(entry: Any) -> Optional[Dict[str, Any]]:
    """
    整理單筆提醒設定；缺標籤、時間格式錯誤或種類不明都回傳 None（跳過該筆，
    不讓一筆壞資料毀掉整份設定）。
    Normalize one reminder. A missing label, a bad time or an unknown kind gives
    None, so one broken entry is skipped instead of breaking the whole list.
    """
    if not isinstance(entry, dict):
        return None
    label = str(entry.get("label", "")).strip()
    if not label:
        return None
    kind = str(entry.get("kind", KIND_EVERY)).strip().lower()
    enabled = bool(entry.get("enabled", True))
    if kind == KIND_AT:
        moment = parse_time_of_day(entry.get("at"))
        if moment is None:
            return None
        return {"label": label, "kind": KIND_AT, "at": f"{moment[0]:02d}:{moment[1]:02d}",
                "enabled": enabled}
    if kind == KIND_EVERY:
        return {"label": label, "kind": KIND_EVERY,
                "minutes": clamp_every_minutes(entry.get("minutes")), "enabled": enabled}
    return None


def normalize_reminders(entries: Any) -> List[Dict[str, Any]]:
    """整理整份提醒清單，跳過壞掉的項目。"""
    if not isinstance(entries, (list, tuple)):
        return []
    reminders = []
    for entry in entries:
        normalized = normalize_reminder(entry)
        if normalized is not None:
            reminders.append(normalized)
    return reminders


class ReminderTracker:
    """
    追蹤每筆提醒上次響的時間，tick() 回傳這一刻該響的標籤清單。純邏輯，
    時鐘可注入，因此測試可以直接把時間往前撥。
    Track when each reminder last fired; tick() returns the labels due right
    now. Pure logic with an injectable clock, so tests can just move time on.
    """

    def __init__(self, config_provider: Callable[[], Any],
                 now_provider: Callable[[], datetime] = datetime.now) -> None:
        self._config_provider = config_provider
        self._now = now_provider
        self._last_fired: Dict[str, datetime] = {}
        # 上一次檢查這則提醒的時間。判斷「有沒有跨過那個時刻」要靠它，
        # 只看「今天響過沒」的話，每次啟動只要時間已經過了就會補響一次。
        # When each reminder was last examined. The "did we cross that moment"
        # test needs it: going by "has it fired today" alone means every launch
        # after the time re-fires it.
        self._last_seen: Dict[str, datetime] = {}

    def reset(self) -> None:
        """忘掉所有紀錄（重新開始計時）。"""
        self._last_fired.clear()
        self._last_seen.clear()

    def _key(self, reminder: Dict[str, Any]) -> str:
        return f"{reminder['kind']}:{reminder['label']}"

    def _due_every(self, reminder: Dict[str, Any], now: datetime, key: str) -> bool:
        last = self._last_fired.get(key)
        if last is None:
            # 第一次看到就開始計時，不會一啟動就響
            # First sighting starts the clock, so nothing fires the moment you launch.
            self._last_fired[key] = now
            return False
        return now - last >= timedelta(minutes=reminder["minutes"])

    def _due_at(self, reminder: Dict[str, Any], now: datetime, key: str) -> bool:
        moment = parse_time_of_day(reminder["at"])
        if moment is None:
            return False
        target = now.replace(hour=moment[0], minute=moment[1], second=0, microsecond=0)
        previous = self._last_seen.get(key)
        self._last_seen[key] = now
        if previous is None:
            # 第一次看到只記時間，不響。和 _due_every 一樣的原則：不然
            # 「09:00 吃藥」在 10 點、13 點、18 點各開一次程式就會響三次。
            # First sighting only starts the clock, as in _due_every: otherwise a
            # 09:00 reminder fires again at every launch that day - 10:00, 13:30,
            # 18:45, each one another toast.
            return False
        if previous >= target or now < target:
            # 那個時刻不在「上次檢查到現在」之間
            # The moment does not fall between the previous check and now.
            return False
        last = self._last_fired.get(key)
        # 每天只響一次：同一天已經響過就跳過
        # Once a day: skip when it already fired today.
        return last is None or last.date() != now.date()

    def tick(self) -> List[str]:
        """回傳此刻到期的提醒標籤（並記下響過的時間）。"""
        now = self._now()
        due: List[str] = []
        for reminder in normalize_reminders(self._config_provider()):
            if not reminder["enabled"]:
                continue
            key = self._key(reminder)
            fired = (self._due_every(reminder, now, key) if reminder["kind"] == KIND_EVERY
                     else self._due_at(reminder, now, key))
            if fired:
                self._last_fired[key] = now
                due.append(reminder["label"])
        return due


class ReminderService(QObject):
    """把 ReminderTracker 接上 QTimer，到期時發出 reminder_due 訊號。"""

    reminder_due = Signal(str)

    def __init__(self, config_provider: Callable[[], Any],
                 now_provider: Callable[[], datetime] = datetime.now,
                 interval_ms: int = 20000, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.tracker = ReminderTracker(config_provider, now_provider)
        self._timer = QTimer(self)
        self._timer.setInterval(max(1000, int(interval_ms)))
        self._timer.timeout.connect(self.poll_once)

    def start(self) -> None:
        front_engine_logger.info("[Reminder] start")
        self._timer.start()

    def stop(self) -> None:
        front_engine_logger.info("[Reminder] stop")
        self._timer.stop()

    def poll_once(self) -> None:
        """檢查一次（測試會直接呼叫）。"""
        try:
            due = self.tracker.tick()
        except Exception as error:  # pragma: no cover - defensive boundary
            front_engine_logger.warning(f"[Reminder] tick error: {error!r}")
            return
        for label in due:
            front_engine_logger.info(f"[Reminder] due | {label}")
            self.reminder_due.emit(label)
