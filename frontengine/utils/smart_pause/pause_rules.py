"""
智慧暫停規則：依「全螢幕程式在前景」「改用電池供電」「指定的程式取得焦點」
三種條件決定要不要暫時收起覆蓋層。純邏輯、不依賴 Qt，方便測試。

Smart-pause rules: decide whether the overlays should stand down because a
fullscreen app is in front, the machine moved to battery power, or one of the
user's named apps took focus. Pure logic - no Qt - so it is easy to test.
"""
from __future__ import annotations

from pathlib import PurePath
from typing import Any, Dict, Iterable, List, Optional

# 觸發暫停的原因（回報給呼叫端，方便記錄與顯示）
# Why the pause fired, reported back for logging and display.
REASON_FULLSCREEN = "fullscreen"
REASON_BATTERY = "battery"
REASON_APP = "app"

DEFAULT_RULES: Dict[str, Any] = {
    # 全螢幕程式（遊戲、投影片）在前景時暫停——預設開啟，維持原本行為。
    # Pause while a fullscreen app (a game, a slide deck) is in front - on by
    # default, which is what this feature did before the other rules existed.
    "fullscreen": True,
    # 改用電池供電時暫停（筆電外出時省電）。
    # Pause once the machine runs on battery, to save power on the move.
    "battery": False,
    # 這些程式取得焦點時暫停，例如剪輯或繪圖軟體。
    # Pause while one of these apps has focus, e.g. an editor or a DAW.
    "apps": [],
}


def normalize_app_name(name: Any) -> str:
    """
    把完整路徑或執行檔名正規化成可比較的名稱：去掉目錄、去掉 .exe、轉小寫。
    Normalize a path or executable name for comparison: drop the directory and
    any .exe suffix, then lowercase it.
    """
    if name is None:
        return ""
    text = str(name).strip().strip('"').strip("'")
    if not text:
        return ""
    base = PurePath(text.replace("\\", "/")).name or text
    if base.lower().endswith(".exe"):
        base = base[:-4]
    return base.strip().lower()


def parse_app_list(value: Any) -> List[str]:
    """
    把使用者輸入的程式清單（逗號或換行分隔的字串，或已經是序列）整理成
    正規化、去重、保持輸入順序的名稱清單。
    Turn the user's app list - a comma/newline separated string, or an actual
    sequence - into normalized names, de-duplicated, in the order given.
    """
    if value is None:
        return []
    if isinstance(value, str):
        raw: Iterable[Any] = value.replace("\n", ",").split(",")
    elif isinstance(value, (list, tuple, set)):
        raw = value
    else:
        return []
    names: List[str] = []
    for item in raw:
        name = normalize_app_name(item)
        if name and name not in names:
            names.append(name)
    return names


def app_matches(active_app: Any, apps: Any) -> bool:
    """前景程式是否在清單裡（比較前兩邊都會正規化）。"""
    active = normalize_app_name(active_app)
    if not active:
        return False
    return active in parse_app_list(apps)


def pause_reason(rules: Optional[Dict[str, Any]] = None, fullscreen: bool = False,
                 on_battery: bool = False, active_app: Any = None) -> Optional[str]:
    """
    回傳第一個成立的暫停原因，都不成立時回傳 None。順序固定為全螢幕、電池、
    指定程式，這樣記錄下來的原因才穩定可預期。
    The first rule that fires, or None when none do. The order - fullscreen,
    battery, app - is fixed so the reported reason stays predictable.
    """
    config = rules if isinstance(rules, dict) else DEFAULT_RULES
    if fullscreen and config.get("fullscreen", True):
        return REASON_FULLSCREEN
    if on_battery and config.get("battery", False):
        return REASON_BATTERY
    if app_matches(active_app, config.get("apps")):
        return REASON_APP
    return None


def should_pause(rules: Optional[Dict[str, Any]] = None, fullscreen: bool = False,
                 on_battery: bool = False, active_app: Any = None) -> bool:
    """是否應該暫停（pause_reason 的布林版本）。"""
    return pause_reason(rules, fullscreen=fullscreen,
                        on_battery=on_battery, active_app=active_app) is not None
