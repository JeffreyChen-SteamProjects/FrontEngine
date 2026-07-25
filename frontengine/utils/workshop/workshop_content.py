"""
Steam 創意工坊內容匯入：Steam 會把訂閱的項目下載到
`steamapps/workshop/content/<appid>/<itemid>/`，這裡就掃那個資料夾，把每個
項目辨識成「寵物動作包」或「預設集」，讓使用者訂閱後直接能用。

注意範圍：**發布**到創意工坊需要 Steamworks SDK 與 App 憑證，不在這裡；
本模組只做免相依、唯讀的「已訂閱內容 -> 可用內容」那一半。

Import Steam Workshop content. Steam downloads subscribed items to
`steamapps/workshop/content/<appid>/<itemid>/`, so this scans that folder and
recognises each item as a pet pack or a preset — subscribe in Steam, use it here.

Scope note: *publishing* to the Workshop needs the Steamworks SDK and app
credentials and is deliberately not attempted. This is the dependency-free,
read-only half: installed items become usable content.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from frontengine.utils.logging.loggin_instance import front_engine_logger

# FrontEngine 的 Steam App ID（商店頁 /app/2793470/）
# FrontEngine's Steam App ID, from its store page.
APP_ID = "2793470"

KIND_PET_PACK = "pet_pack"
KIND_PRESET = "preset"
KIND_MEDIA = "media"

_PET_STATE_FILES = ("walk", "idle", "sleep", "climb", "fall", "drag")
_IMAGE_SUFFIXES = (".gif", ".webp", ".png", ".jpg", ".jpeg")
_MANIFEST_NAME = "pet.json"


def default_library_paths() -> List[Path]:
    """
    各平台 Steam 預設安裝位置（找不到也沒關係，使用者可以自己指定路徑）。
    Where Steam usually lives per platform; the user can always point at it.
    """
    home = Path.home()
    if sys.platform == "win32":
        return [Path("C:/Program Files (x86)/Steam"), Path("C:/Steam"), home / "Steam"]
    if sys.platform == "darwin":
        return [home / "Library" / "Application Support" / "Steam"]
    return [home / ".steam" / "steam", home / ".local" / "share" / "Steam"]


def workshop_content_dir(steam_path, app_id: str = APP_ID) -> Optional[Path]:
    """
    回傳某個 Steam 安裝路徑底下本程式的創意工坊內容資料夾；不存在回傳 None。
    """
    try:
        candidate = Path(steam_path) / "steamapps" / "workshop" / "content" / str(app_id)
    except (TypeError, ValueError):
        return None
    return candidate if candidate.is_dir() else None


def find_workshop_dir(app_id: str = APP_ID, extra_paths=()) -> Optional[Path]:
    """在預設位置與額外指定的位置裡找出創意工坊內容資料夾。"""
    for base in list(extra_paths) + default_library_paths():
        found = workshop_content_dir(base, app_id)
        if found is not None:
            return found
    return None


def classify_item(folder) -> Optional[str]:
    """
    判斷一個創意工坊項目是什麼：動作包（有 walk/idle… 圖或 pet.json）、
    預設集（有 .json 預設檔）、單純媒體（只有圖片）。都不像則回傳 None。
    """
    try:
        path = Path(folder)
        if not path.is_dir():
            return None
        names = [entry.name.lower() for entry in path.iterdir() if entry.is_file()]
    except OSError:
        return None
    if _MANIFEST_NAME in names:
        return KIND_PET_PACK
    stems = {Path(name).stem for name in names}
    if stems & set(_PET_STATE_FILES):
        return KIND_PET_PACK
    if any(name.endswith(".json") for name in names):
        return KIND_PRESET
    if any(name.endswith(_IMAGE_SUFFIXES) for name in names):
        return KIND_MEDIA
    return None


def read_item_title(folder) -> str:
    """
    取項目名稱：優先用動作包 pet.json 裡的 name，其次用資料夾名稱（項目 ID）。
    """
    try:
        manifest = Path(folder) / _MANIFEST_NAME
        if manifest.is_file():
            data = json.loads(manifest.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("name"), str):
                return data["name"]
    except (OSError, ValueError, TypeError):
        pass
    return Path(folder).name


def scan_workshop_items(content_dir) -> List[Dict[str, str]]:
    """
    列出已訂閱且能辨識的項目：[{"id", "kind", "title", "path"}]。
    List the recognisable subscribed items.
    """
    items: List[Dict[str, str]] = []
    try:
        base = Path(content_dir)
        if not base.is_dir():
            return items
        for entry in sorted(base.iterdir()):
            if not entry.is_dir():
                continue
            kind = classify_item(entry)
            if kind is None:
                front_engine_logger.debug(f"[workshop] unrecognised item: {entry.name}")
                continue
            items.append({
                "id": entry.name,
                "kind": kind,
                "title": read_item_title(entry),
                "path": str(entry),
            })
    except OSError as error:
        front_engine_logger.warning(f"[workshop] scan failed: {error!r}")
    return items


def preset_files(item_path) -> List[str]:
    """回傳項目裡的預設集檔案（.json）。"""
    try:
        base = Path(item_path)
        if not base.is_dir():
            return []
        return sorted(str(path) for path in base.iterdir()
                      if path.is_file() and path.suffix.lower() == ".json"
                      and path.name.lower() != _MANIFEST_NAME)
    except OSError:
        return []
