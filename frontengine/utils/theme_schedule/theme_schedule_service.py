from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from frontengine.utils.logging.loggin_instance import front_engine_logger

# 預設的日間/夜間主題與切換時間
# Default day/night themes and switch hours.
DEFAULT_THEME_SCHEDULE: Dict[str, Any] = {
    "enabled": False,
    "day_theme": "light_blue.xml",
    "night_theme": "dark_amber.xml",
    "day_start_hour": 7,
    "night_start_hour": 19,
}


def _coerce_hour(value: Any, default: int) -> int:
    try:
        return int(value) % 24
    except (TypeError, ValueError):
        return default


def resolve_scheduled_theme(config: Dict[str, Any], hour: int) -> Optional[str]:
    """
    依當前小時回傳應套用的主題名稱；停用或設定不完整時回傳 None。
    Return the theme name to apply for `hour`, or None when disabled /
    misconfigured. Day window is [day_start, night_start); otherwise night.
    Handles a window that wraps past midnight (day_start > night_start).
    """
    if not isinstance(config, dict) or not config.get("enabled"):
        return None
    day_theme = config.get("day_theme") or DEFAULT_THEME_SCHEDULE["day_theme"]
    night_theme = config.get("night_theme") or DEFAULT_THEME_SCHEDULE["night_theme"]
    day_start = _coerce_hour(config.get("day_start_hour"), DEFAULT_THEME_SCHEDULE["day_start_hour"])
    night_start = _coerce_hour(config.get("night_start_hour"), DEFAULT_THEME_SCHEDULE["night_start_hour"])
    hour = hour % 24
    if day_start == night_start:
        return night_theme
    if day_start < night_start:
        is_day = day_start <= hour < night_start
    else:  # window wraps midnight, e.g. day 20:00 -> 06:00
        is_day = hour >= day_start or hour < night_start
    return day_theme if is_day else night_theme


class ThemeScheduleService(QObject):
    """
    週期性依時間切換日間/夜間主題。設定與時鐘皆可注入以利測試。
    Periodically switch between a day and night theme based on the clock.
    Both the config and the clock are injectable for testing.
    """

    theme_changed = Signal(str)

    def __init__(
        self,
        config_provider: Callable[[], Dict[str, Any]],
        hour_provider: Optional[Callable[[], int]] = None,
        interval_ms: int = 60000,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._config_provider = config_provider
        self._hour_provider = hour_provider or (lambda: datetime.now().hour)
        self._current: Optional[str] = None
        self._timer = QTimer(self)
        self._timer.setInterval(max(1000, int(interval_ms)))
        self._timer.timeout.connect(self._poll)

    def start(self) -> None:
        front_engine_logger.info("[ThemeSchedule] start")
        self._timer.start()
        self._poll()  # apply immediately rather than after the first interval

    def stop(self) -> None:
        front_engine_logger.info("[ThemeSchedule] stop")
        self._timer.stop()

    def _poll(self) -> None:
        try:
            config = self._config_provider() or {}
            theme = resolve_scheduled_theme(config, int(self._hour_provider()))
        except Exception as error:  # pragma: no cover - defensive boundary
            front_engine_logger.warning(f"[ThemeSchedule] poll error: {error!r}")
            return
        if theme and theme != self._current:
            self._current = theme
            self.theme_changed.emit(theme)

    def poll_once(self) -> None:
        """Run a single poll immediately (used by tests)."""
        self._poll()
