from os import getcwd
from pathlib import Path
from typing import Any, Dict, List, Optional

from frontengine.utils.json.json_repository import JsonRepository
from frontengine.utils.preset_schedule.preset_schedule_service import DEFAULT_PRESET_SCHEDULE
from frontengine.utils.theme_schedule.theme_schedule_service import DEFAULT_THEME_SCHEDULE

# 預設全域快速鍵：動作名稱 -> pynput 組合字串
# Default global hotkeys: action name -> pynput combo string
default_hotkeys: Dict[str, str] = {
    "close_all": "<ctrl>+<shift>+<f12>",
    "hide_all": "<ctrl>+<shift>+<f11>",
    "show_all": "<ctrl>+<shift>+<f10>",
    "mute_all": "<ctrl>+<shift>+<f9>",
    "opacity_up": "<ctrl>+<shift>+<up>",
    "opacity_down": "<ctrl>+<shift>+<down>",
    "dashboard_next": "<ctrl>+<shift>+<right>",
    "toggle_lock": "<ctrl>+<shift>+l",
}

user_setting_dict: Dict[str, Any] = {
    "language": "English",
    "theme": "dark_amber.xml",
    "hotkeys": dict(default_hotkeys),
    # 啟動時自動套用的預設集名稱（空字串表示停用）
    # Preset auto-applied on launch (empty string disables it)
    "startup_preset": "",
    # 偵測到全螢幕程式時自動隱藏覆蓋層
    # Auto-hide overlays while a fullscreen app is running
    "smart_pause": True,
    # 依時間自動切換日/夜主題
    # Auto-switch day/night theme by time of day
    "theme_schedule": dict(DEFAULT_THEME_SCHEDULE),
    # 每天在指定時間自動套用預設集
    # Auto-apply a preset at a configured time each day
    "preset_schedule": dict(DEFAULT_PRESET_SCHEDULE),
    # 使用者拖曳過的覆蓋層位置：類別名稱 -> [x, y, 寬, 高]
    # Overlay positions the user dragged into place: class name -> [x, y, w, h]
    "overlay_geometry": {},
    # 啟動時還原上次的頁面設定
    # Restore the previous session's page settings on launch
    "restore_last_session": False,
    # 智慧暫停規則：{"fullscreen": bool, "battery": bool, "apps": [程式名稱]}
    # Smart-pause rules: which conditions stand the overlays down.
    "smart_pause_rules": {"fullscreen": True, "battery": False, "apps": []},
    # 前景程式對應的預設集：{程式名稱: 預設集名稱}
    # Per-app profiles: {app name: preset name}
    "app_profiles": {},
    # 自訂提醒：[{"label", "kind": "every"/"at", "minutes"/"at", "enabled"}]
    # Custom reminders, shown as a toast when they come due.
    "reminders": [],
    # 便利貼內容與位置，以及要不要在啟動時開回來
    # Sticky note contents and positions, and whether to reopen them on launch.
    "sticky_notes": [],
    "sticky_notes_restore": False,
    # 看板模式：依序輪播預設集（預設關閉）
    # Signage mode: rotate through presets; off by default.
    "signage": {"enabled": False, "presets": [], "interval_minutes": 5, "hide_window": True},
    # 手機遙控（會開一個本機網路埠，預設關閉）與 MIDI 綁定
    # The phone remote opens a local network port and is off by default;
    # plus the MIDI control bindings.
    "phone_remote": {"enabled": False},
    "midi_bindings": {},
    "midi_device": 0,
    # 分享畫面時自動把覆蓋層藏出擷取結果（預設關閉）
    # Hide overlays from the capture while sharing; off by default.
    "screen_share_privacy": {"enabled": False, "apps": []},
    # 使用時間統計（只寫本機檔案、預設關閉）
    # Usage tracking: local file only, off by default.
    "usage_tracking": False,
    # 剪貼簿歷史（預設關閉；未開啟保存時只留在記憶體）
    # Clipboard history: off by default, memory only unless saving is on.
    "clipboard_history": False,
    "clipboard_persist": False,
    "clipboard_entries": [],
    "clipboard_limit": 50,
    # 已儲存的視窗版面：名稱 -> [{title, x, y, width, height}]
    # Saved window layouts: name -> [{title, x, y, width, height}]
    "window_layouts": {},
    # 是否同意把擷取畫面送到 Anthropic 讀取文字（預設不同意）
    # Consent to send captures to Anthropic for reading text (off by default).
    "screen_text_consent": False,
    # 覆蓋層畫質檔位：high / balanced / saver
    # Overlay quality tier: high / balanced / saver.
    "quality_tier": "high",
    # 是否載入 plugins/ 資料夾裡的外掛（外掛與本程式同權限，預設關閉）
    # Load plugins from plugins/? They run with our privileges, so: off by default.
    "load_plugins": False,
    # 桌面寵物心情值（0~100），跨工作階段保存
    # Desktop pet mood (0..100), persisted across sessions
    "pet_mood": 60,
    # 桌面寵物飽足值（0~100）
    # Desktop pet fullness (0..100)
    "pet_hunger": 70,
    # 桌面寵物親密度（累積互動）
    # Desktop pet affection (accumulated interactions)
    "pet_affection": 0,
    # 桌面寵物場景時間軸：[{"at": 秒, "say"/"sleep"/"feed"/"behaviour": ...}, ...]
    # Desktop pet scene timeline of scheduled actions
    "pet_timeline": [],
}


def _repository() -> JsonRepository:
    return JsonRepository(Path(getcwd()) / "user_setting.json")


def write_user_setting() -> Path:
    return _repository().save(user_setting_dict)


def read_user_setting() -> Path:
    repo = _repository()
    repo.load_into(user_setting_dict)
    return repo.path


def is_stored(key: str) -> bool:
    """
    這個鍵是不是真的寫在設定檔裡（而不是這裡的預設值）。

    載入是把檔案 merge 到預設值上，所以載入之後 `user_setting_dict` 分不出兩者。
    「使用者從沒挑過語言」和「使用者挑了英文」要做的事不一樣，得問檔案本身。

    Whether `key` is actually in the settings file rather than a default here.

    Loading merges the file over the defaults, so afterwards `user_setting_dict`
    cannot tell the two apart. "The user never chose a language" and "the user
    chose English" call for different behaviour, so this asks the file itself.
    """
    repo = _repository()
    if not repo.exists():
        return False
    data = repo.load()
    return isinstance(data, dict) and key in data


def export_user_setting(destination: Path) -> Path:
    """將目前所有設定寫出到指定路徑 / Write all current settings to `destination`."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    return JsonRepository(destination).save(user_setting_dict)


def import_user_setting(source: Path) -> None:
    """
    從檔案匯入設定並合併、持久化。非 JSON 物件會丟出 ValueError。
    Import settings from a file, merge them in, and persist. A non-object
    document raises ValueError.
    """
    repo = JsonRepository(Path(source))
    if not repo.exists():
        raise FileNotFoundError(f"File not found: {source}")
    data = repo.load()
    if not isinstance(data, dict):
        raise ValueError("Settings file must contain a JSON object")
    user_setting_dict.update(data)
    write_user_setting()


def save_overlay_geometry(kind: str, x: int, y: int, width: int, height: int) -> None:
    """記住某類覆蓋層被拖曳到的位置與大小 / Remember where an overlay was dragged."""
    geometry = user_setting_dict.get("overlay_geometry")
    if not isinstance(geometry, dict):
        geometry = {}
        user_setting_dict["overlay_geometry"] = geometry
    geometry[str(kind)] = [int(x), int(y), int(width), int(height)]


def get_overlay_geometry(kind: str) -> Optional[List[int]]:
    """回傳該類覆蓋層記住的 [x, y, 寬, 高]；沒有或格式錯誤回傳 None。"""
    geometry = user_setting_dict.get("overlay_geometry")
    if not isinstance(geometry, dict):
        return None
    values = geometry.get(str(kind))
    if not isinstance(values, (list, tuple)) or len(values) != 4:
        return None
    try:
        return [int(value) for value in values]
    except (TypeError, ValueError):
        return None


def clear_overlay_geometry() -> None:
    """忘掉所有記住的覆蓋層位置，讓它們回到各自預設的顯示方式。"""
    user_setting_dict["overlay_geometry"] = {}


def get_hotkey_bindings() -> Dict[str, str]:
    """
    回傳「pynput 組合字串 -> 動作名稱」的對應，供 HotkeyService 使用。
    合併內建預設與使用者設定，並忽略型別錯誤的項目，避免手動編輯過的
    user_setting.json 造成崩潰。
    Return a ``combo -> action`` mapping for HotkeyService. Merges built-in
    defaults with user settings and skips malformed entries so a hand-edited
    user_setting.json cannot crash startup.
    """
    # Invert to combo -> action (HotkeyService keys on the combo).
    bindings: Dict[str, str] = {}
    for action, combo in get_hotkey_action_map().items():
        bindings[combo] = action
    return bindings


def get_hotkey_action_map() -> Dict[str, str]:
    """
    回傳「動作名稱 -> 組合鍵」對應，合併內建預設與使用者設定（忽略型別錯誤）。
    Return an ``action -> combo`` map, merging built-in defaults with user
    settings (skipping malformed entries).
    """
    merged: Dict[str, str] = dict(default_hotkeys)
    user_hotkeys = user_setting_dict.get("hotkeys")
    if isinstance(user_hotkeys, dict):
        for action, combo in user_hotkeys.items():
            if not isinstance(action, str) or not isinstance(combo, str):
                continue
            if combo.strip():
                merged[action] = combo.strip()
            else:
                # 明確存成空字串＝使用者把那個欄位清空，也就是要解除綁定。
                # 當成「沒設定」而沿用內建預設，等於那個快速鍵永遠拿不掉。
                # An explicit empty string means the user cleared that field, i.e.
                # unbind. Reading it as "unset" and falling back to the built-in
                # default made the shortcut impossible to get rid of.
                merged.pop(action, None)
    return merged


def get_recent_files(category: str) -> List[str]:
    """回傳某分類最近使用的檔案路徑（最新在前）。型別錯誤的項目會被略過。"""
    recents = user_setting_dict.get("recent_files")
    if not isinstance(recents, dict):
        return []
    entries = recents.get(category)
    if not isinstance(entries, list):
        return []
    return [path for path in entries if isinstance(path, str) and path]


def add_recent_file(category: str, path: str, limit: int = 10) -> None:
    """
    將 path 記錄到某分類最近使用清單的最前面（去重、截斷至 limit）。
    Record `path` at the front of a category's recent list (deduped, capped).
    """
    if not isinstance(path, str) or not path:
        return
    recents = user_setting_dict.get("recent_files")
    if not isinstance(recents, dict):
        recents = {}
        user_setting_dict["recent_files"] = recents
    entries = [p for p in get_recent_files(category) if p != path]
    entries.insert(0, path)
    recents[category] = entries[: max(1, int(limit))]
