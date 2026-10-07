"""Normalize legacy scenes and a versioned envelope without losing entries."""
from __future__ import annotations

import copy
import math
import os
from pathlib import Path

from frontengine.utils.imervue.puppet_asset import finite_parameters
from frontengine.utils.scene_format.scene_animation import validate_animation

SCENE_FORMAT = 'frontengine.scene'
SCENE_VERSION = 1
ASSET_FIELDS = ('text_file', 'file_path', 'script_path')


def resolve_asset(value: str, base_dir: Path | None) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Scene asset path must be a nonempty string')
    path = Path(value)
    if base_dir is None:
        return str(path)
    root = Path(base_dir).resolve()
    resolved = (root / path).resolve()
    if not path.is_absolute() and not resolved.is_relative_to(root):
        raise ValueError('Relative scene asset is outside the scene directory')
    return str(resolved)


def normalize_scene(data: object, base_dir: Path | None = None) -> dict:
    if not isinstance(data, dict):
        raise ValueError('A scene must be a JSON object')
    if data.get('format') == SCENE_FORMAT:
        if type(data.get('version')) is not int or data['version'] != SCENE_VERSION:
            raise ValueError('Unsupported scene version')
        data = data.get('entries')
        if not isinstance(data, dict):
            raise ValueError('Scene entries must be an object')
    entries = copy.deepcopy(data)
    for entry in entries.values():
        if not isinstance(entry, dict):
            raise ValueError('Each scene entry must be an object')
        if 'animation' in entry:
            entry['animation'] = validate_animation(entry['animation'])
        for field in ASSET_FIELDS:
            if field in entry and entry[field] is not None:
                entry[field] = resolve_asset(entry[field], base_dir)
        if entry.get('type') == 'PUPPET':
            if 'file_path' not in entry:
                raise ValueError('PUPPET entry requires file_path')
            _validate_puppet_entry(entry)
    return entries


def scene_envelope(entries: dict, base_dir: Path | None = None) -> dict:
    normalized = normalize_scene(entries)
    if base_dir is not None:
        root = Path(base_dir).resolve()
        for entry in normalized.values():
            for field in ASSET_FIELDS:
                value = entry.get(field)
                if value and Path(value).is_absolute() and Path(value).resolve().is_relative_to(root):
                    entry[field] = Path(os.path.relpath(value, root)).as_posix()
    return {'format': SCENE_FORMAT, 'version': SCENE_VERSION, 'entries': normalized}


def _validate_puppet_entry(entry: dict) -> None:
    """Reject invalid native widget arguments before allocating its runtime."""
    finite_parameters(entry.get('parameters', {}))
    for field in ('x', 'y', 'z', 'opacity'):
        if field in entry:
            value = entry[field]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f'PUPPET {field} must be finite')
    if not 0 <= entry.get('opacity', 100) <= 100:
        raise ValueError('PUPPET opacity must be between 0 and 100')
    size = entry.get('size', [240, 360])
    if not isinstance(size, (list, tuple)) or len(size) != 2 or any(
            type(value) is not int or not 16 <= value <= 4096 for value in size):
        raise ValueError('PUPPET size must contain two integers between 16 and 4096')
    for field in ('motion', 'expression'):
        if field in entry and entry[field] is not None and not isinstance(entry[field], str):
            raise ValueError(f'PUPPET {field} must be a string')
