from __future__ import annotations

import re
from os import getcwd
from pathlib import Path
from typing import Any, Dict, List, Optional

from frontengine.utils.json.json_repository import JsonRepository

_FILENAME_SAFE = re.compile(r"[^A-Za-z0-9_\- ]+")


def _default_dir() -> Path:
    return Path(getcwd()) / "presets"


def _sanitize(name: str) -> str:
    sanitized = _FILENAME_SAFE.sub("_", name).strip().strip("_")
    if not sanitized:
        raise ValueError("Preset name must contain at least one safe character")
    return sanitized


class PresetRepository:
    """
    One JSON file per preset under `<cwd>/presets/`. Each document is a
    flat mapping of setting-page key -> page state dict, with the preset
    name itself stored under the reserved "__preset_name__" key.
    """

    def __init__(self, directory: Optional[Path] = None) -> None:
        self._dir: Path = directory or _default_dir()

    @property
    def directory(self) -> Path:
        return self._dir

    def list_presets(self) -> List[str]:
        if not self._dir.exists():
            return []
        return sorted(path.stem for path in self._dir.glob("*.json"))

    def _path_for(self, name: str) -> Path:
        return self._dir / f"{_sanitize(name)}.json"

    def save(self, name: str, data: Dict[str, Any]) -> Path:
        self._dir.mkdir(parents=True, exist_ok=True)
        payload: Dict[str, Any] = {"__preset_name__": name}
        payload.update(data)
        return JsonRepository(self._path_for(name)).save(payload)

    def load(self, name: str) -> Dict[str, Any]:
        repo = JsonRepository(self._path_for(name))
        if not repo.exists():
            raise FileNotFoundError(f"Preset not found: {name}")
        data = repo.load()
        if not isinstance(data, dict):
            return {}
        return {key: value for key, value in data.items() if key != "__preset_name__"}

    def delete(self, name: str) -> bool:
        path = self._path_for(name)
        if path.exists():
            path.unlink()
            return True
        return False
