"""
第一次啟動時，跟著 Steam 客戶端的語言走。

在 Steam 上安裝的人已經挑過一次語言了，再讓程式用英文開起來、要他自己去選單裡
再挑一次，是白費工。這裡只讀 Steam 客戶端目前設定的語言，**不需要 Steamworks
SDK、不需要 App ID、也不會連線**——Windows 讀登錄檔，其他平台讀 Steam 自己的
``registry.vdf``。

只在使用者還沒挑過語言時套用（設定檔裡沒有 ``language`` 這個鍵）。挑過之後就以
使用者的選擇為準，否則選單改了語言、下次開啟又被改回去，看起來就像選單壞了。

Follow the Steam client's language on first launch.

Someone who installed through Steam has already chosen a language once; opening
in English and asking them to choose again in a menu is wasted work. This reads
the language the Steam client is set to and nothing else: **no Steamworks SDK,
no App ID, no network**. Windows reads the registry, other platforms read
Steam's own ``registry.vdf``.

It applies only while the user has not chosen a language yet - no ``language``
key in the settings file. After that their choice wins, otherwise changing the
language in the menu would be undone on the next launch and the menu would look
broken.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Optional

from frontengine.utils.logging.loggin_instance import front_engine_logger

# Steam 的語言代碼 -> 這個程式註冊的語言名稱。
# 只列本程式真的有翻譯的七種；Steam 支援的其他語言會落到 None，也就是維持預設。
# Steam's language codes to the names this application registers. Only the seven
# that are actually translated appear here; any other Steam language falls
# through to None, which leaves the default in place.
STEAM_LANGUAGE_MAP = {
    "english": "English",
    "tchinese": "Traditional_Chinese",
    "schinese": "Simplified_Chinese",
    "german": "Deutsch",
    "russian": "Russian",
    "french": "France",
    "italian": "Italy",
}

_VDF_LANGUAGE = re.compile(r'"Language"\s+"([^"]+)"', re.IGNORECASE)


def _windows_language_code() -> Optional[str]:
    """從登錄檔讀 Steam 客戶端語言（只讀，不寫）。"""
    if sys.platform != "win32":
        return None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Valve\Steam") as key:
            value, _ = winreg.QueryValueEx(key, "Language")
        return str(value).strip().lower() or None
    except OSError:
        # Steam 沒裝、或這台機器上沒有這個值 / Steam absent, or no such value here.
        return None


def _registry_vdf_paths() -> list[Path]:
    """macOS 與 Linux 上 Steam 存 registry.vdf 的位置。"""
    home = Path.home()
    if sys.platform == "darwin":
        return [home / "Library" / "Application Support" / "Steam" / "registry.vdf"]
    return [
        home / ".steam" / "registry.vdf",
        home / ".steam" / "steam" / "registry.vdf",
        home / ".local" / "share" / "Steam" / "registry.vdf",
    ]


def _vdf_language_code(paths=None) -> Optional[str]:
    """
    從 registry.vdf 撈出語言。這裡不寫 VDF 解析器：需要的只有一個字串，
    多寫一個格式解析器就多一份要維護、會出錯的東西。
    Pull the language out of registry.vdf. No VDF parser here: one string is all
    this needs, and a format parser would be one more thing to maintain and get
    wrong.
    """
    for path in (paths if paths is not None else _registry_vdf_paths()):
        try:
            if not Path(path).is_file():
                continue
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        match = _VDF_LANGUAGE.search(text)
        if match:
            return match.group(1).strip().lower() or None
    return None


def steam_language_code() -> Optional[str]:
    """Steam 客戶端目前的語言代碼，讀不到就回傳 None。"""
    return _windows_language_code() or _vdf_language_code()


def steam_language() -> Optional[str]:
    """
    對應到本程式的語言名稱；Steam 沒裝、讀不到、或那個語言沒有翻譯時回傳 None。
    The matching language name for this application, or None when Steam is not
    installed, could not be read, or is set to a language with no translation.
    """
    code = steam_language_code()
    if not code:
        return None
    name = STEAM_LANGUAGE_MAP.get(code)
    if name is None:
        front_engine_logger.info(
            f"[SteamLanguage] Steam is set to '{code}', which has no translation here")
    return name
