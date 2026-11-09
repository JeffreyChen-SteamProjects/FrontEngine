"""
Steam 創意工坊內容匯入：Steam 會把訂閱的項目下載到
`steamapps/workshop/content/<appid>/<itemid>/`，這裡就掃那個資料夾，把每個
項目辨識成場景、預設集或家園內容，讓使用者訂閱後直接能用。

本模組保留免相依、唯讀的離線資料夾辨識；原生發布與同步由 Workshop 服務處理。

Import Steam Workshop content. Steam downloads subscribed items to
`steamapps/workshop/content/<appid>/<itemid>/`, so this scans that folder and
recognises each item as a scene, a preset or pet home content — subscribe in Steam, use it here.
Sprite pet packs and picture folders are no longer recognised: pets are layered only.

This remains the dependency-free, read-only offline folder recognizer.
Native publishing and synchronization are handled by the separate Workshop service.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.workshop.workshop_manifest import is_legacy_preset, read_manifest, safe_path

# FrontEngine 的 Steam App ID（商店頁 /app/2793470/）
# FrontEngine's Steam App ID, from its store page.
APP_ID = "2793470"

KIND_PRESET = "preset"
KIND_SCENE = "scene"
HOME_PACK_KINDS = ("home_furniture", "home_theme")     # a content pack folder as the entry
KIND_HOME_BLUEPRINT = "home_blueprint"



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
    判斷一個創意工坊項目是什麼：有 workshop.json 的依其種類，舊格式只認預設集（有 .json 預設檔）。
    都不像則回傳 None。
    What a Workshop item is: its workshop.json kind, or a legacy preset folder; None otherwise.
    """
    try:
        path = Path(folder)
        if not path.is_dir():
            return None
        if (path / "workshop.json").exists():
            return read_manifest(path)["kind"]
        files = [entry for entry in path.iterdir() if entry.is_file()]
        names = [entry.name.lower() for entry in files]
    except (OSError, ValueError, UnicodeError):
        return None
    if "pet.json" in names:         # a sprite pet pack: unsupported since pets are layered only
        return None
    if any(entry.suffix.lower() == ".json" and is_legacy_preset(entry) for entry in files):
        return KIND_PRESET
    return None


def read_item_title(folder) -> str:
    """
    取項目名稱：優先用 workshop.json 的標題，其次用資料夾名稱（項目 ID）。
    """
    try:
        if (Path(folder) / "workshop.json").exists():
            return read_manifest(Path(folder))["title"]
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


def home_pack_roots(content_dir) -> List[Path]:
    """The pack folders of subscribed furniture and theme items; the pet home checks each one itself."""
    roots = []
    for item in scan_workshop_items(content_dir):
        if item["kind"] in HOME_PACK_KINDS:
            try:
                roots.append(safe_path(Path(item["path"]), read_manifest(Path(item["path"]))["entry"]))
            except (OSError, ValueError) as error:               # UnicodeError is a ValueError
                front_engine_logger.warning(f"[workshop] home pack {item['id']}: {error}")
    return roots


def missing_requirements(item_path, installed: set) -> List[str]:
    """The content packs a subscribed item needs that are not installed (from its manifest)."""
    try:
        manifest = read_manifest(Path(item_path))
    except (OSError, ValueError):
        return []
    return [pack for pack in manifest.get("requires", []) if pack not in installed]


def preset_files(item_path) -> List[str]:
    """回傳項目裡的預設集檔案（.json）。"""
    try:
        base = Path(item_path)
        if not base.is_dir():
            return []
        return sorted(str(path) for path in base.iterdir()
                      if path.is_file() and path.suffix.lower() == ".json"
                      and is_legacy_preset(path))
    except OSError:
        return []
