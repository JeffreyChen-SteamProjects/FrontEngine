from __future__ import annotations

import copy
import json
import re
import zipfile
from os import getcwd
from pathlib import Path
from typing import Any, Dict, List, Optional

from frontengine.utils.json.json_repository import JsonRepository

_FILENAME_SAFE = re.compile(r"[^A-Za-z0-9_\- ]+")
# 打包時媒體檔在 zip 內的資料夾前綴
# In-archive folder prefix for bundled media files.
_MEDIA_PREFIX = "media/"
_PRESET_MEMBER = "preset.json"


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

    def exists(self, name: str) -> bool:
        """Return True when a preset with this (sanitized) name is stored."""
        return self._path_for(name).exists()

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

    def export_preset(self, name: str, destination: Path) -> Path:
        """
        Copy an existing preset document to an arbitrary location so the
        user can share or back it up. Raises FileNotFoundError when the
        preset does not exist.
        """
        source = self._path_for(name)
        if not source.exists():
            raise FileNotFoundError(f"Preset not found: {name}")
        # `destination` is a location the user picked in a native Save dialog,
        # not remote/untrusted input, so writing there is intended behaviour.
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        # destination 是使用者在原生「另存新檔」對話框裡挑的位置，不是遠端輸入。
        # destination is where the user pointed a native Save dialog, not remote input.
        destination.write_text(  # NOSONAR
            source.read_text(encoding="utf-8"), encoding="utf-8")
        return destination

    def import_preset(self, source: Path) -> str:
        """
        Read a preset document from an arbitrary location, validate it is a
        JSON object, and store it under the presets directory. The preset
        name is taken from the reserved "__preset_name__" key when present,
        otherwise from the file stem. Returns the stored preset name.
        """
        source = Path(source)
        repo = JsonRepository(source)
        if not repo.exists():
            raise FileNotFoundError(f"File not found: {source}")
        data = repo.load()
        if not isinstance(data, dict):
            raise ValueError("Preset file must contain a JSON object")
        raw_name = data.get("__preset_name__")
        name = raw_name if isinstance(raw_name, str) and raw_name.strip() else source.stem
        payload = {key: value for key, value in data.items() if key != "__preset_name__"}
        self.save(name, payload)
        return _sanitize(name)

    def export_package(self, name: str, destination: Path) -> Path:
        """
        將預設集連同其引用的媒體檔打包成 .zip，方便攜帶分享。
        Bundle a preset and the media files it references into a portable
        .zip. Media paths inside the archived preset are rewritten to
        ``media/<filename>``. Raises FileNotFoundError when the preset is
        missing.
        """
        source = self._path_for(name)
        if not source.exists():
            raise FileNotFoundError(f"Preset not found: {name}")
        document = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise ValueError("Preset file must contain a JSON object")

        rewritten = copy.deepcopy(document)
        media_map: Dict[str, str] = {}  # archive name -> original path
        used_names: set = set()
        for section in rewritten.values():
            if not isinstance(section, dict):
                continue
            for key, value in tuple(section.items()):
                if isinstance(value, str) and value and Path(value).is_file():
                    archive_name = self._unique_media_name(Path(value).name, used_names)
                    used_names.add(archive_name)
                    media_map[archive_name] = value
                    section[key] = f"{_MEDIA_PREFIX}{archive_name}"

        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(_PRESET_MEMBER, json.dumps(rewritten, indent=4))
            for archive_name, original in media_map.items():
                archive.write(original, f"{_MEDIA_PREFIX}{archive_name}")
        return destination

    def import_package(self, source: Path) -> str:
        """
        匯入 export_package 產生的 .zip：解開媒體檔到 presets/media/<名稱>/，
        將預設集內的 media/ 路徑改寫為實際位置後存檔。對 zip-slip 具防護。
        Import a .zip produced by export_package: extract media into
        ``presets/media/<name>/``, rewrite the preset's ``media/`` paths to the
        extracted locations, and store it. Protected against zip-slip.
        """
        source = Path(source)
        if not source.exists() or not zipfile.is_zipfile(source):
            raise ValueError(f"Not a valid preset package: {source}")
        with zipfile.ZipFile(source, "r") as archive:
            document = _read_package_preset(archive)
            name = _package_name(document, source)
            media_dir = self._dir / "media" / _sanitize(name)
            media_dir.mkdir(parents=True, exist_ok=True)
            _extract_media(archive, media_dir)

        _rewrite_media_paths(document, media_dir)
        payload = {key: value for key, value in document.items() if key != "__preset_name__"}
        self.save(name, payload)
        return _sanitize(name)

    @staticmethod
    def _unique_media_name(filename: str, used: set) -> str:
        """避免 zip 內媒體檔名衝突 / Disambiguate colliding media filenames."""
        if filename not in used:
            return filename
        stem, suffix = Path(filename).stem, Path(filename).suffix
        index = 1
        while f"{stem}_{index}{suffix}" in used:
            index += 1
        return f"{stem}_{index}{suffix}"


def _read_package_preset(archive: zipfile.ZipFile) -> Dict[str, Any]:
    """讀出封包裡的 preset.json；缺檔或格式不對就擲出 ValueError。"""
    try:
        raw = archive.read(_PRESET_MEMBER)
    except KeyError as error:
        raise ValueError("Package missing preset.json") from error
    document = json.loads(raw.decode("utf-8"))
    if not isinstance(document, dict):
        raise ValueError("Package preset.json must be a JSON object")
    return document


def _package_name(document: Dict[str, Any], source: Path) -> str:
    """封包裡記的名稱；沒記或是空白就用檔名。"""
    raw_name = document.get("__preset_name__")
    return raw_name if isinstance(raw_name, str) and raw_name.strip() else source.stem


def _extract_media(archive: zipfile.ZipFile, media_dir: Path) -> Dict[str, Path]:
    """
    把封包裡的媒體檔解到 media_dir。**只用檔名的最後一段**，這是對 zip-slip
    的防護：封包裡寫成 ../../ 的路徑不會逃出這個資料夾。
    Extract the package's media into media_dir. **Only the flat basename is
    ever used** - that is the zip-slip guard: an entry named ../../ cannot
    escape this directory.
    """
    extracted: Dict[str, Path] = {}
    for member in archive.namelist():
        if not member.startswith(_MEDIA_PREFIX) or member.endswith("/"):
            continue
        target = media_dir / Path(member).name
        with archive.open(member) as source_file, open(target, "wb") as target_file:
            target_file.write(source_file.read())
        extracted[member] = target
    return extracted


def _rewrite_media_paths(document: Dict[str, Any], media_dir: Path) -> None:
    """把預設集裡的 media/ 相對路徑改寫成解開後的實際位置。"""
    for section in document.values():
        if not isinstance(section, dict):
            continue
        for key, value in tuple(section.items()):
            if isinstance(value, str) and value.startswith(_MEDIA_PREFIX):
                section[key] = str(media_dir / Path(value).name)
