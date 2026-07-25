"""
動態文字來源：讓文字覆蓋層不只顯示固定字串，還能顯示時鐘、日期、倒數、碼表、
系統資訊或天氣。全部是純邏輯（不依賴 Qt），實際資料由外部注入的 provider 提供。

Dynamic text sources so a text overlay can show a clock, date, countdown,
stopwatch, system stats or weather instead of a fixed string. Pure logic (no Qt)
— live data arrives through injected providers.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Dict, Optional

# 可選的文字來源 / Available text sources
SOURCE_STATIC = "static"
SOURCE_CLOCK = "clock"
SOURCE_DATE = "date"
SOURCE_COUNTDOWN = "countdown"
SOURCE_STOPWATCH = "stopwatch"
SOURCE_SYSTEM = "system"
SOURCE_WEATHER = "weather"

SOURCE_KINDS = (
    SOURCE_STATIC, SOURCE_CLOCK, SOURCE_DATE, SOURCE_COUNTDOWN,
    SOURCE_STOPWATCH, SOURCE_SYSTEM, SOURCE_WEATHER,
)

# 各來源的預設樣板 / Default template per source
DEFAULT_TEMPLATES: Dict[str, str] = {
    SOURCE_STATIC: "",
    SOURCE_CLOCK: "%H:%M:%S",
    SOURCE_DATE: "%Y-%m-%d %a",
    SOURCE_COUNTDOWN: "25",
    SOURCE_STOPWATCH: "",
    SOURCE_SYSTEM: "CPU {cpu}%  RAM {ram}%",
    SOURCE_WEATHER: "{temperature}°C  {description}",
}

# 更新頻率（毫秒）：秒級的來源每秒更新，系統與天氣不必那麼頻繁
# Refresh interval per source; system and weather do not need per-second updates.
REFRESH_INTERVALS_MS: Dict[str, int] = {
    SOURCE_STATIC: 0,
    SOURCE_CLOCK: 1000,
    SOURCE_DATE: 60000,
    SOURCE_COUNTDOWN: 1000,
    SOURCE_STOPWATCH: 1000,
    SOURCE_SYSTEM: 2000,
    SOURCE_WEATHER: 600000,
}


def format_duration(total_seconds) -> str:
    """把秒數格式化成 H:MM:SS（不足一小時則 MM:SS）；負數視為 0。"""
    try:
        seconds = max(0, int(float(total_seconds)))
    except (TypeError, ValueError):
        seconds = 0
    hours, remainder = divmod(seconds, 3600)
    minutes, second = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{second:02d}"
    return f"{minutes:02d}:{second:02d}"


def parse_countdown_target(template: str, now: datetime) -> Optional[datetime]:
    """
    把倒數樣板解析成目標時間：純數字＝幾分鐘後，`HH:MM`＝下一個該時刻，
    `YYYY-MM-DD HH:MM`＝指定時間。解析不出來回傳 None。
    """
    text = str(template or "").strip()
    if not text:
        return None
    try:
        return now + timedelta(minutes=float(text))
    except ValueError:
        pass
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, pattern)
        except ValueError:
            continue
    try:
        clock_time = datetime.strptime(text, "%H:%M")
    except ValueError:
        return None
    target = now.replace(hour=clock_time.hour, minute=clock_time.minute, second=0, microsecond=0)
    return target if target > now else target + timedelta(days=1)


def format_mapping(template: str, values: Dict[str, object], fallback: str) -> str:
    """
    以 values 套用 `{key}` 樣板；樣板空白或有未知欄位時退回 fallback 樣板。
    Fill a ``{key}`` template from `values`, falling back when it is blank or
    references a key that does not exist.
    """
    text = str(template or "").strip() or fallback
    try:
        return text.format(**values)
    except (KeyError, IndexError, ValueError):
        try:
            return fallback.format(**values)
        except (KeyError, IndexError, ValueError):
            return ""


class TextSource:
    """
    依來源種類產生要顯示的文字。時間由 now_provider 提供（測試可注入固定時間），
    系統資訊與天氣由對應的 provider 提供，取不到時顯示 `--`。

    Produce the text to display for a given source kind. Time comes from
    `now_provider` (injectable for tests); system stats and weather come from
    their providers, showing `--` when unavailable.
    """

    UNAVAILABLE = "--"

    def __init__(self, kind: str = SOURCE_STATIC, template: str = "",
                 now_provider: Callable[[], datetime] = datetime.now,
                 stats_provider: Optional[Callable[[], dict]] = None,
                 weather_provider: Optional[Callable[[], dict]] = None) -> None:
        self.kind = kind if kind in SOURCE_KINDS else SOURCE_STATIC
        self.template = str(template or "")
        self._now = now_provider
        self._stats_provider = stats_provider
        self._weather_provider = weather_provider
        self._started_at: Optional[datetime] = None
        self._countdown_target: Optional[datetime] = None

    @property
    def refresh_interval_ms(self) -> int:
        """該來源建議的更新間隔；靜態文字為 0（不需要計時器）。"""
        return REFRESH_INTERVALS_MS.get(self.kind, 1000)

    def start(self) -> None:
        """開始計時（碼表與倒數用），呼叫多次會重新開始。"""
        self._started_at = self._now()
        self._countdown_target = parse_countdown_target(
            self.template or DEFAULT_TEMPLATES[SOURCE_COUNTDOWN], self._started_at)

    def text(self) -> str:
        """回傳目前應顯示的文字。"""
        if self.kind == SOURCE_STATIC:
            return self.template
        if self.kind in (SOURCE_CLOCK, SOURCE_DATE):
            return self._strftime()
        if self.kind == SOURCE_COUNTDOWN:
            return self._countdown_text()
        if self.kind == SOURCE_STOPWATCH:
            return format_duration((self._now() - (self._started_at or self._now())).total_seconds())
        if self.kind == SOURCE_SYSTEM:
            return self._provider_text(self._stats_provider)
        return self._provider_text(self._weather_provider)

    def _strftime(self) -> str:
        template = self.template.strip() or DEFAULT_TEMPLATES[self.kind]
        try:
            return self._now().strftime(template)
        except (ValueError, TypeError):
            return self._now().strftime(DEFAULT_TEMPLATES[self.kind])

    def _countdown_text(self) -> str:
        if self._countdown_target is None:
            self.start()
        if self._countdown_target is None:
            return format_duration(0)
        return format_duration((self._countdown_target - self._now()).total_seconds())

    def finished(self) -> bool:
        """倒數是否已歸零 / Whether a countdown has reached zero."""
        if self.kind != SOURCE_COUNTDOWN or self._countdown_target is None:
            return False
        return self._now() >= self._countdown_target

    def _provider_text(self, provider) -> str:
        """把 provider 的欄位套進樣板；provider 缺席或出錯時顯示 `--`。"""
        if provider is None:
            return self.UNAVAILABLE
        try:
            values = provider()
        except Exception:  # pragma: no cover - defensive around live providers
            return self.UNAVAILABLE
        if not values:
            return self.UNAVAILABLE
        readable = {key: (self.UNAVAILABLE if value is None else value) for key, value in values.items()}
        return format_mapping(self.template, readable, DEFAULT_TEMPLATES[self.kind])
