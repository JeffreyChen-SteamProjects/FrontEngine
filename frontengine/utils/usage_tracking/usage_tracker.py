"""
使用時間統計：記錄每個程式在前景待了多久，用來回答「今天時間花到哪去了」。

**這是敏感資料，所以設計上就綁死三件事**：只寫在本機的一個 JSON 檔（不外傳、
不上傳）、**預設關閉**、而且隨時可以一鍵清除。使用者沒開啟時，這裡不會被
呼叫，也不會有任何檔案產生。

Usage tracking: how long each app spent in the foreground, so "where did the
day go" has an answer.

**This is sensitive data, so three things are built in, not optional**: it is
written to one local JSON file and never sent anywhere, it is **off by
default**, and it can be cleared in one click. While it is off nothing calls
in here and no file is created.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from frontengine.utils.json.json_repository import JsonRepository
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.smart_pause.pause_rules import normalize_app_name

USAGE_FILE = "frontengine_usage.json"
# 單次取樣最多算這麼多秒，避免電腦睡醒後把整段離線時間算成「在用某程式」
# The most one sample may add, so waking from sleep does not book hours of
# downtime against whatever app happened to be in front.
MAX_SAMPLE_SECONDS = 120
# 只留最近這麼多天，統計檔不會無限長大
# Only this many days are kept, so the file cannot grow forever.
MAX_DAYS = 60


def day_key(moment: Optional[datetime] = None) -> str:
    """把時間換成 YYYY-MM-DD 的日期鍵。"""
    value = moment or datetime.now()
    return value.date().isoformat() if isinstance(value, datetime) else str(value)


def clamp_seconds(seconds: Any) -> float:
    """單次取樣的秒數：負數當 0，過長的一段截到上限。"""
    try:
        value = float(seconds)
    except (TypeError, ValueError):
        return 0.0
    if value <= 0:
        return 0.0
    return min(value, float(MAX_SAMPLE_SECONDS))


def normalize_history(data: Any) -> Dict[str, Dict[str, float]]:
    """
    把讀進來的統計整理成 {日期: {程式: 秒數}}；壞掉的項目直接跳過，
    不讓一筆手改壞的資料毀掉整份紀錄。
    Normalize the stored history to {day: {app: seconds}}, skipping anything
    malformed so one hand-edited entry cannot destroy the whole record.
    """
    history: Dict[str, Dict[str, float]] = {}
    if not isinstance(data, dict):
        return history
    for day, apps in data.items():
        if not isinstance(apps, dict):
            continue
        cleaned: Dict[str, float] = {}
        for app, seconds in apps.items():
            name = normalize_app_name(app)
            try:
                value = float(seconds)
            except (TypeError, ValueError):
                continue
            if name and value > 0:
                cleaned[name] = cleaned.get(name, 0.0) + value
        if cleaned:
            history[str(day)] = cleaned
    return history


def format_duration(seconds: Any) -> str:
    """把秒數說成人看得懂的長度（1h 05m / 12m / 45s）。"""
    try:
        total = max(0, int(float(seconds)))
    except (TypeError, ValueError):
        return "0s"
    if total >= 3600:
        return f"{total // 3600}h {(total % 3600) // 60:02d}m"
    if total >= 60:
        return f"{total // 60}m"
    return f"{total}s"


class UsageTracker:
    """
    累積每天每個程式的前景時間。純資料處理，時鐘與儲存都可注入，因此測試
    不需要真的等時間過去，也不會在磁碟留下東西。
    Accumulate foreground time per app per day. Pure bookkeeping with an
    injectable clock and store, so tests neither wait nor touch the disk.
    """

    def __init__(self, repository: Optional[JsonRepository] = None,
                 now_provider: Callable[[], datetime] = datetime.now) -> None:
        self._repository = repository
        self._now = now_provider
        self.history: Dict[str, Dict[str, float]] = {}
        self._last_app: str = ""
        self._last_moment: Optional[datetime] = None

    # --- persistence -----------------------------------------------------
    def load(self) -> None:
        """讀回本機的統計檔（沒有檔案就是空的）。"""
        if self._repository is None or not self._repository.exists():
            return
        try:
            self.history = normalize_history(self._repository.load())
        except Exception as error:  # pragma: no cover - defensive file boundary
            front_engine_logger.warning(f"[UsageTracker] load failed: {error!r}")
            self.history = {}

    def save(self) -> bool:
        """
        把統計寫回本機檔案（只有這一個檔，不會送到任何地方）。沒有任何紀錄時
        **不會建立檔案**——關著統計的使用者，磁碟上就不該多出一個檔。
        Write the history back to the local file. With nothing recorded it
        **creates no file**: a user who leaves tracking off should not find one
        on disk. Returns whether anything was written.
        """
        if self._repository is None:
            return False
        data = self.trimmed()
        if not data:
            return False
        try:
            self._repository.save(data)
            return True
        except Exception as error:  # pragma: no cover - defensive file boundary
            front_engine_logger.warning(f"[UsageTracker] save failed: {error!r}")
            return False

    def clear(self) -> None:
        """
        忘掉所有紀錄，連磁碟上的檔案也刪掉——「清除」就該是真的清除。
        Forget everything, including the file on disk: "clear" has to mean it.
        """
        self.history = {}
        self._last_app = ""
        self._last_moment = None
        if self._repository is None:
            return
        try:
            path = Path(self._repository.path)
            if path.is_file():
                path.unlink()
                front_engine_logger.info(f"[UsageTracker] cleared | removed {path}")
        except OSError as error:  # pragma: no cover - defensive file boundary
            front_engine_logger.warning(f"[UsageTracker] clear failed: {error!r}")

    def trimmed(self) -> Dict[str, Dict[str, float]]:
        """只保留最近 MAX_DAYS 天的紀錄。"""
        days = sorted(self.history)[-MAX_DAYS:]
        return {day: dict(self.history[day]) for day in days}

    # --- recording -------------------------------------------------------
    def observe(self, app: Any, moment: Optional[datetime] = None) -> float:
        """
        看到「現在的前景程式是誰」。把上一次觀察到現在的這段時間記到上一個
        程式頭上，並回傳實際記進去的秒數（第一次觀察沒有可記的時間）。
        Note which app is in front now. The gap since the previous observation
        is booked against the previous app; the seconds actually recorded come
        back (the very first observation records nothing).
        """
        now = moment or self._now()
        name = normalize_app_name(app)
        recorded = 0.0
        if self._last_app and self._last_moment is not None:
            recorded = clamp_seconds((now - self._last_moment).total_seconds())
            if recorded > 0:
                day = self.history.setdefault(day_key(self._last_moment), {})
                day[self._last_app] = day.get(self._last_app, 0.0) + recorded
        self._last_app = name
        self._last_moment = now if name else None
        return recorded

    def pause(self) -> None:
        """
        暫停累積（使用者離開鍵盤、或統計被關掉）。下一次 observe 會重新開始
        計時，不會把離開的那段算進去。
        Stop accumulating - the user stepped away, or tracking was switched
        off. The next observe starts a fresh interval instead of billing the
        gap to whatever was in front.
        """
        self._last_app = ""
        self._last_moment = None

    # --- reading ---------------------------------------------------------
    def totals_for(self, day: Optional[str] = None) -> Dict[str, float]:
        """某一天的 {程式: 秒數}；預設今天。"""
        return dict(self.history.get(day or day_key(self._now()), {}))

    def top_apps(self, day: Optional[str] = None, limit: int = 8) -> List[Tuple[str, float]]:
        """某一天用最久的幾個程式，由多到少。"""
        totals = self.totals_for(day)
        ordered = sorted(totals.items(), key=lambda item: (-item[1], item[0]))
        return ordered[:max(1, int(limit))]

    def total_seconds(self, day: Optional[str] = None) -> float:
        """某一天的總時數。"""
        return float(sum(self.totals_for(day).values()))

    def recent_days(self, days: int = 7) -> List[Tuple[str, float]]:
        """最近幾天的 (日期, 總秒數)，由舊到新，缺的日子補 0。"""
        count = max(1, int(days))
        today = self._now().date()
        result: List[Tuple[str, float]] = []
        for offset in range(count - 1, -1, -1):
            key = date.fromordinal(today.toordinal() - offset).isoformat()
            result.append((key, float(sum(self.history.get(key, {}).values()))))
        return result
