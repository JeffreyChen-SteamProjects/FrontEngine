"""
條件式規則：「當 <條件> 成立時，做 <動作>」。

這個專案已經有四套各自為政的排程（智慧暫停、預設集排程、主題排程、桌布安靜
時段），每一套只認得自己那一種條件，也各自配一個對話框。規則引擎補的是它們
之間的空隙——「平日晚上七點以後、而且不是在打電動的時候，套用夜間預設集」這種
組合，原本任何一套都寫不出來。既有的四套沒有被拿掉：它們各自把一件事做得很好，
這裡只是讓條件可以組合。

**邊緣觸發**是這裡最重要的一件事：規則是每隔幾秒輪詢一次的，如果條件成立就動作，
那「套用預設集」會每隔幾秒重套一次，使用者手動改的任何設定都會在下一次輪詢被
蓋掉。所以動作只在「從不成立變成成立」的那一刻發生一次，直到條件不再成立才會
重新武裝。

Conditional rules: "when <conditions> hold, do <action>".

This project already has four separate schedulers - smart pause, preset
schedule, theme schedule, wallpaper quiet hours - each knowing one kind of
condition and each with its own dialog. The engine fills the gap between them:
"on weekdays after 19:00, unless I am gaming, apply the night preset" is a
combination none of them can express. The four are not replaced; each does its
own job well, and this only makes conditions composable.

**Edge triggering** is the important part. Rules are polled every few seconds,
so firing whenever the condition holds would re-apply a preset every few
seconds and overwrite anything the user changed by hand in between. An action
fires once on the transition into truth, and re-arms only after the condition
goes false again.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.smart_pause.pause_rules import app_matches, parse_app_list

DEFAULT_INTERVAL_MS = 5000

# 動作。全部對應到主視窗既有的能力，這個引擎不會自己長出新的副作用。
# The actions, all mapping to something the main window can already do: the
# engine grows no side effects of its own.
ACTION_APPLY_PRESET = "apply_preset"
ACTION_HIDE_ALL = "hide_all"
ACTION_SHOW_ALL = "show_all"
ACTION_CLOSE_ALL = "close_all"
ACTION_QUALITY_TIER = "quality_tier"
ACTIONS = (ACTION_APPLY_PRESET, ACTION_HIDE_ALL, ACTION_SHOW_ALL,
           ACTION_CLOSE_ALL, ACTION_QUALITY_TIER)
# 需要附帶一個值的動作（預設集名稱、畫質檔位）
# Actions that carry a value: a preset name, a quality tier.
VALUE_ACTIONS = (ACTION_APPLY_PRESET, ACTION_QUALITY_TIER)


def parse_minute_of_day(text: Any) -> Optional[int]:
    """把 "19:30" 解析成從午夜起算的分鐘數；格式不對回傳 None。"""
    if text is None:
        return None
    parts = str(text).strip().split(":")
    if len(parts) != 2:
        return None
    try:
        hour, minute = int(parts[0]), int(parts[1])
    except (TypeError, ValueError):
        return None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return hour * 60 + minute


def in_time_window(minute: int, start: Optional[int], end: Optional[int]) -> bool:
    """
    現在的分鐘數落在 [start, end) 裡嗎。支援跨午夜（22:00 到 06:00），
    因為「睡前」這種時段本來就跨午夜——不支援的話那個情境就寫不出來。
    Whether the minute falls in [start, end), wrapping past midnight: "late
    evening" genuinely crosses midnight, and without wrapping it cannot be
    expressed at all.
    """
    if start is None and end is None:
        return True
    if start is None or end is None:
        return True
    if start == end:
        return True
    if start < end:
        return start <= minute < end
    return minute >= start or minute < end


def normalize_days(value: Any) -> List[int]:
    """把星期整理成排序過、不重複、0..6 的清單；空的代表「每天」。"""
    if value is None:
        return []
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        value = [value]
    if not isinstance(value, (list, tuple, set)):
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


def normalize_rule(entry: Any) -> Optional[Dict[str, Any]]:
    """
    整理一條規則；缺標籤、動作不認得、或該帶值卻沒帶值的一律回傳 None
    （跳過壞掉的那一條，不要讓整份設定失效）。
    Tidy one rule, or None when it has no label, an unknown action, or an
    action that needs a value and has none - skip the broken rule rather than
    invalidating the whole file.
    """
    if not isinstance(entry, dict):
        return None
    label = str(entry.get("label", "")).strip()
    action = str(entry.get("action", "")).strip()
    if not label or action not in ACTIONS:
        return None
    value = str(entry.get("value", "")).strip()
    if action in VALUE_ACTIONS and not value:
        return None
    when = entry.get("when") if isinstance(entry.get("when"), dict) else {}
    condition: Dict[str, Any] = {
        "days": normalize_days(when.get("days")),
        "from": parse_minute_of_day(when.get("from")),
        "to": parse_minute_of_day(when.get("to")),
        "apps": parse_app_list(when.get("apps")),
        "idle_minutes": _coerce_positive(when.get("idle_minutes")),
    }
    for flag in ("fullscreen", "battery"):
        condition[flag] = bool(when[flag]) if isinstance(when.get(flag), bool) else None
    return {
        "label": label,
        "enabled": bool(entry.get("enabled", True)),
        "action": action,
        "value": value,
        "when": condition,
    }


def _coerce_positive(value: Any) -> Optional[int]:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def normalize_rules(entries: Any) -> List[Dict[str, Any]]:
    """整理整份規則清單，跳過壞掉的項目。"""
    if not isinstance(entries, (list, tuple)):
        return []
    rules = []
    for entry in entries:
        rule = normalize_rule(entry)
        if rule is not None:
            rules.append(rule)
    return rules


def has_any_condition(condition: Dict[str, Any]) -> bool:
    """
    這條規則有沒有寫任何條件。全空的規則永遠成立，等於「每次啟動就套用」，
    多半是使用者還沒填完——當成不成立，比讓它一直觸發好。
    Whether anything was actually specified. An empty condition is always true,
    which means "fire once at startup" and is almost always a half-filled rule;
    treating it as never true beats letting it fire.
    """
    if condition.get("days") or condition.get("apps"):
        return True
    if condition.get("from") is not None or condition.get("to") is not None:
        return True
    if condition.get("idle_minutes") is not None:
        return True
    return any(condition.get(flag) is not None for flag in ("fullscreen", "battery"))


def evaluate(rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """
    這條規則此刻成立嗎。context 的欄位缺了就當「這一項不符合」——讀不到前景
    程式時，不該把「指定程式在前景」當成成立。
    Whether the rule holds right now. A missing context field counts as not
    matching: when the foreground app cannot be read, "this app has focus" is
    not satisfied.
    """
    if not rule.get("enabled", True):
        return False
    condition = rule.get("when") or {}
    if not has_any_condition(condition):
        return False

    now = context.get("now")
    if condition.get("days"):
        if not isinstance(now, datetime) or now.weekday() not in condition["days"]:
            return False
    if condition.get("from") is not None or condition.get("to") is not None:
        if not isinstance(now, datetime):
            return False
        if not in_time_window(now.hour * 60 + now.minute,
                              condition.get("from"), condition.get("to")):
            return False
    if condition.get("apps") and not app_matches(context.get("app"), condition["apps"]):
        return False
    for flag, key in (("fullscreen", "fullscreen"), ("battery", "on_battery")):
        wanted = condition.get(flag)
        if wanted is None:
            continue
        actual = context.get(key)
        if not isinstance(actual, bool) or actual is not wanted:
            return False
    idle_minutes = condition.get("idle_minutes")
    if idle_minutes is not None:
        idle_seconds = context.get("idle_seconds")
        if not isinstance(idle_seconds, (int, float)) or idle_seconds < idle_minutes * 60:
            return False
    return True


class RuleTracker:
    """
    記住每條規則上一次的成立狀態，只在「不成立 -> 成立」時回報要執行。
    純邏輯，時鐘與環境都由 context 傳入。
    Remembers each rule's previous truth and reports only the false-to-true
    transitions. Pure logic; the clock and environment arrive in the context.
    """

    def __init__(self) -> None:
        self._active: Dict[str, bool] = {}

    def reset(self) -> None:
        self._active = {}

    def active(self, label: str) -> bool:
        return self._active.get(label, False)

    def tick(self, rules: Any, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """回傳這一刻剛剛成立、需要執行的規則。"""
        fired = []
        seen = set()
        for rule in normalize_rules(rules):
            label = rule["label"]
            seen.add(label)
            holds = evaluate(rule, context)
            if holds and not self._active.get(label, False):
                fired.append(rule)
            self._active[label] = holds
        # 已經被刪掉的規則要忘掉，否則同名規則之後再建立時會被當成「還在成立」
        # 而永遠不觸發。
        # Forget deleted rules: otherwise recreating one with the same label
        # would look like it was still true and never fire again.
        self._active = {label: holds for label, holds in self._active.items() if label in seen}
        return fired


class RuleEngineService(QObject):
    """
    把 RuleTracker 接上 QTimer：定期取得環境、算出剛成立的規則，逐一送出。
    環境來源可注入（測試餵固定值）。
    RuleTracker on a QTimer: sample the environment, work out which rules just
    became true, and emit them one by one. The environment source is
    injectable.
    """

    rule_fired = Signal(dict)

    def __init__(self, rules_provider=None, context_provider=None,
                 interval_ms: int = DEFAULT_INTERVAL_MS,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._rules_provider = rules_provider or (lambda: [])
        self._context_provider = context_provider or default_context
        self.tracker = RuleTracker()
        self._timer = QTimer(self)
        self._timer.setInterval(max(1000, int(interval_ms)))
        self._timer.timeout.connect(self.poll_once)

    def running(self) -> bool:
        return self._timer.isActive()

    def start(self) -> None:
        if not self._timer.isActive():
            front_engine_logger.info("[RuleEngineService] start")
            self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self.tracker.reset()

    def poll_once(self) -> List[Dict[str, Any]]:
        try:
            rules = self._rules_provider() or []
            context = self._context_provider() or {}
        except Exception as error:  # pragma: no cover - defensive boundary
            front_engine_logger.warning(f"[RuleEngineService] source failed: {error!r}")
            return []
        fired = self.tracker.tick(rules, context)
        for rule in fired:
            front_engine_logger.info(
                f"[RuleEngineService] fired {rule['label']} -> {rule['action']}")
            self.rule_fired.emit(rule)
        return fired


def default_context() -> Dict[str, Any]:
    """
    正式執行時的環境：時間、前景程式、是否全螢幕、是否用電池、閒置秒數。
    每一項都沿用既有的偵測器，這個引擎不自己實作任何平台呼叫。
    The live environment: time, foreground app, fullscreen, battery, idle. Each
    reuses an existing detector; the engine implements no platform calls.
    """
    from frontengine.utils.platform_info.platform_info import (
        active_app_name, idle_seconds, read_battery,
    )
    from frontengine.utils.smart_pause.smart_pause_service import (
        battery_detector, windows_fullscreen_detector,
    )

    battery = read_battery()
    return {
        "now": datetime.now(),
        "app": active_app_name(),
        "fullscreen": windows_fullscreen_detector(),
        "on_battery": battery_detector() if battery is not None else False,
        "idle_seconds": idle_seconds(),
    }
