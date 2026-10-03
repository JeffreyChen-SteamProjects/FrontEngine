"""Validate declarations and bind in-process plugin grants to their content."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

API_VERSION = 1
PERMISSIONS = frozenset({'filesystem', 'network', 'screen_capture', 'microphone',
                         'native_code', 'clipboard', 'input', 'ui'})
MAX_PLUGIN_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class PluginManifest:
    plugin_id: str
    entrypoint: Path
    permissions: tuple[str, ...]
    digest: str
    legacy: bool = False

    @property
    def grant_key(self) -> str:
        return f'{self.plugin_id}:{self.entrypoint.resolve()}'


def _content_digest(root: Path, files: list[Path]) -> str:
    digest = hashlib.sha256()
    size = 0
    for path in sorted(files):
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('Plugin paths must stay inside the plugin directory')
        size += path.stat().st_size
        if size > MAX_PLUGIN_BYTES:
            raise ValueError('Plugin exceeds the content size limit')
        digest.update(path.relative_to(root).as_posix().encode('utf-8'))
        digest.update(b'\0')
        with path.open('rb') as source:
            for block in iter(lambda: source.read(65536), b''):
                digest.update(block)
        digest.update(b'\0')
    return digest.hexdigest()


def read_manifest(entrypoint: Path) -> PluginManifest:
    entrypoint = Path(entrypoint).absolute()
    if entrypoint.is_symlink() or entrypoint.parent.is_symlink():
        raise ValueError('Plugin paths cannot be symbolic links')
    packaged = entrypoint.name == 'plugin.py'
    root = entrypoint.parent
    manifest_path = root / 'plugin.json' if packaged else entrypoint.with_suffix('.json')
    files = [p for p in root.rglob('*') if p.is_symlink() or
             (p.is_file() and (packaged or p.suffix in {'.py', '.pyc', '.pyo'}))]
    if len(files) > 4096:
        raise ValueError('Plugin contains too many files')
    legacy = not manifest_path.exists()
    if legacy:
        plugin_id, permissions = entrypoint.parent.name if packaged else entrypoint.stem, ('full_trust',)
    else:
        if manifest_path.stat().st_size > 65536 or manifest_path.is_symlink():
            raise ValueError('Invalid plugin manifest size or path')
        raw = json.loads(manifest_path.read_text(encoding='utf-8'))
        plugin_id, permissions = _parse_manifest(raw, entrypoint.name)
        if not packaged:
            files.append(manifest_path)
    return PluginManifest(plugin_id, entrypoint, tuple(permissions), _content_digest(root, files), legacy)


def _parse_manifest(raw: object, filename: str) -> tuple[str, list[str]]:
    if not isinstance(raw, dict) or type(raw.get('version')) is not int or raw['version'] != 1:
        raise ValueError('Unsupported plugin manifest version')
    api = raw.get('api_version')
    if type(api) is not int or not 1 <= api <= API_VERSION:
        raise ValueError('Unsupported plugin API version')
    plugin_id = raw.get('id')
    if not isinstance(plugin_id, str) or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', plugin_id) is None:
        raise ValueError('Invalid plugin id')
    if raw.get('entrypoint') != filename:
        raise ValueError('Plugin entrypoint must name the discovered file without a path')
    permissions = raw.get('permissions')
    if not isinstance(permissions, list) or any(not isinstance(p, str) or p not in PERMISSIONS for p in permissions):
        raise ValueError('Invalid or unknown plugin permissions')
    return plugin_id, sorted(set(permissions))


def authorize_plugin(manifest: PluginManifest, grants: dict, authorizer=None) -> bool:
    if grants.get(manifest.grant_key) == manifest.digest:
        return True
    if authorizer is None or not authorizer(manifest):
        return False
    # Check again after the user responds: code may change while a dialog is open.
    current = read_manifest(manifest.entrypoint)
    if current != manifest:
        return False
    grants[manifest.grant_key] = manifest.digest
    return True
