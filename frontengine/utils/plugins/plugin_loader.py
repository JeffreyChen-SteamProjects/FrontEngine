"""
外掛載入：把 `plugins/` 資料夾裡的 Python 模組載入，並讓它們用
`FrontEngine_EXTEND_TAB` 註冊自己的分頁。

**信任模型（重要）**：外掛就是 Python 程式，載入後擁有和本程式相同的權限——
無法沙箱化。因此此功能**預設關閉**，必須由使用者明確開啟，且每次載入都會把
載入了哪些檔案寫進 log。只安裝你信任的外掛。

Plugin loading: import Python modules from a `plugins/` folder and let them
register their own tabs through `FrontEngine_EXTEND_TAB`.

**Trust model (important)**: a plugin is Python code and runs with exactly the
same privileges as this application — it cannot be sandboxed. So loading is
**off by default**, must be turned on explicitly, and every load is logged.
Only install plugins you trust.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Dict, List, Optional

from frontengine.utils.logging.loggin_instance import front_engine_logger

PLUGIN_DIR_NAME = "plugins"
MANIFEST_NAME = "plugin.json"
ENTRY_NAME = "plugin.py"


def plugin_dir(base: Optional[str] = None) -> Path:
    """外掛資料夾位置（預設為工作目錄下的 plugins/）。"""
    from os import getcwd

    return Path(base) if base else Path(getcwd()) / PLUGIN_DIR_NAME


def discover_plugins(base: Optional[str] = None) -> List[Path]:
    """
    列出可載入的外掛：`plugins/<名稱>/plugin.py`，或 `plugins/<名稱>.py`。
    Candidate plugins: `plugins/<name>/plugin.py`, or `plugins/<name>.py`.
    """
    directory = plugin_dir(base)
    found: List[Path] = []
    try:
        if not directory.is_dir():
            return found
        for entry in sorted(directory.iterdir()):
            if entry.is_dir() and (entry / ENTRY_NAME).is_file():
                found.append(entry / ENTRY_NAME)
            elif entry.is_file() and entry.suffix == ".py" and not entry.name.startswith("_"):
                found.append(entry)
    except OSError as error:
        front_engine_logger.warning(f"[plugins] cannot read {directory}: {error!r}")
    return found


def module_name_for(path) -> str:
    """依路徑組出模組名稱，避免和已載入的模組撞名。"""
    path = Path(path)
    stem = path.parent.name if path.name == ENTRY_NAME else path.stem
    return f"frontengine_plugin_{stem}"


def load_plugin_module(path) -> Optional[ModuleType]:
    """
    載入單一外掛模組；失敗只記錄並回傳 None，一個壞外掛不會拖垮其他外掛。
    Import one plugin module; a failure is logged and skipped so one bad plugin
    cannot take the others (or the app) down with it.
    """
    path = Path(path)
    name = module_name_for(path)
    try:
        spec = importlib.util.spec_from_file_location(name, str(path))
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)  # nosec B102 - user-installed plugin, see trust model above
        front_engine_logger.info(f"[plugins] loaded {path}")
        return module
    except Exception as error:  # pragma: no cover - arbitrary third-party code
        front_engine_logger.warning(f"[plugins] failed to load {path}: {error!r}")
        sys.modules.pop(name, None)
        return None


def register_plugin_tabs(module, registry: Dict[str, type]) -> List[str]:
    """
    讓外掛註冊分頁：模組可以提供 `FRONTENGINE_TABS = {"名稱": QWidget 子類別}`，
    或一個 `register(registry)` 函式。回傳實際註冊成功的分頁名稱。

    Let a plugin register tabs: either a `FRONTENGINE_TABS` mapping of name to
    QWidget subclass, or a `register(registry)` function. Returns the names that
    actually landed in the registry.
    """
    added: List[str] = []
    if module is None:
        return added
    tabs = getattr(module, "FRONTENGINE_TABS", None)
    if isinstance(tabs, dict):
        for name, widget in tabs.items():
            if isinstance(name, str) and isinstance(widget, type):
                registry[name] = widget
                added.append(name)
    register = getattr(module, "register", None)
    if callable(register):
        before = set(registry)
        try:
            register(registry)
        except Exception as error:  # pragma: no cover - arbitrary third-party code
            front_engine_logger.warning(f"[plugins] register() failed: {error!r}")
        else:
            added.extend(sorted(set(registry) - before))
    return added


def load_plugins(registry: Dict[str, type], enabled: bool = False,
                 base: Optional[str] = None) -> List[str]:
    """
    載入所有外掛並註冊它們的分頁；`enabled` 為 False（預設）時完全不載入。
    回傳成功註冊的分頁名稱。

    Load every plugin and register its tabs. With `enabled` False — the default —
    nothing is imported at all.
    """
    if not enabled:
        return []
    paths = discover_plugins(base)
    if paths:
        front_engine_logger.warning(
            f"[plugins] loading {len(paths)} plugin(s) with full application privileges; "
            "only install plugins you trust")
    registered: List[str] = []
    for path in paths:
        registered.extend(register_plugin_tabs(load_plugin_module(path), registry))
    return registered
