"""Typed scene/preset reference scans and reviewed file repair with crash rollback."""
from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import json
import re
from pathlib import Path

from frontengine.utils.asset_library.inspect import read_json, inspect_asset
from frontengine.utils.asset_library.repository import AssetRepository, checked_assets
from frontengine.utils.scene_format.scene_document import ASSET_FIELDS, normalize_scene
from frontengine.utils.scene_format.scene_editor_document import validate_geometry
from frontengine.user_setting.preset_history import checked_state
from frontengine.utils.todo.repository import atomic_write

PRESET_FIELDS = {'video': ('video_path',), 'image': ('image_path', 'slideshow_folder'),
                 'gif': ('gif_image_path',), 'pet': ('pet_image_path', 'puppet_script', 'sound'),
                 'sound': ('wav_sound_path', 'player_sound_path'), 'text': ('text_file',)}


def _same(value, path: str, root: Path) -> bool:
    return isinstance(value, str) and bool(value) and (root / value).resolve() == Path(path).resolve()


def rewrite_scene(document: dict, old: str, new: str, base: Path) -> tuple[dict, list[str]]:
    """Change exact path fields while preserving unknown scene metadata and relative peers."""
    normalize_scene(document, base)
    result, locations = deepcopy(document), []
    entries = result['entries'] if result.get('format') == 'frontengine.scene' else result
    if len(entries) > 256:
        raise ValueError('Reference scene exceeds 256 layers')
    for name, entry in entries.items():
        for key in ASSET_FIELDS:
            if _same(entry.get(key), old, base):
                entry[key] = new
                locations.append(str(name) + '/' + key)
    validate_geometry(normalize_scene(result, base))
    return result, locations


def rewrite_preset(document: dict, old: str, new: str, root: Path) -> tuple[dict, list[str]]:
    """Rewrite only known page path fields; literal text/URLs and immutable history stay intact."""
    result, _digest = checked_state(document)
    locations = []
    for page, fields in PRESET_FIELDS.items():
        section = result.get(page)
        if not isinstance(section, dict):
            continue
        for key in fields:
            if _same(section.get(key), old, root):
                section[key] = new
                locations.append(page + '/' + key)
    checked_state(result)
    return result, locations


def protected(path: Path, root: Path) -> bool:
    """Only workspace JSON can be repaired; managed Workshop/package sources stay read-only."""
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        return True
    parts = {part.casefold() for part in resolved.relative_to(root.resolve()).parts}
    if parts & {'.git', '.versions', 'workshop', '.frontengine'}:
        return True
    return any((parent / 'workshop.json').is_file() or parent.is_symlink() or
               (parent.exists() and getattr(parent.lstat(), 'st_file_attributes', 0) & 0x400)
               for parent in (path, *path.parents))


def plan_relink(repository: AssetRepository, identity: str, replacement: str, scene: dict) -> dict:
    """Validate replacement type and collect exact changes for an explicit review."""
    asset = repository.assets[identity]
    replacement = str(Path(replacement).absolute())
    kind, _image = inspect_asset(replacement)
    if kind != asset['kind']:
        raise ValueError('Replacement must have the same asset type')
    if any(entry['id'] != identity and Path(entry['path']) == Path(replacement) for entry in repository.assets.values()):
        raise ValueError('Replacement is already registered as another asset')
    updated, locations = rewrite_scene(scene, asset['path'], replacement, repository.root)
    plan = {'identity': identity, 'old': asset['path'], 'new': replacement,
            'scene_before': deepcopy(scene), 'scene_after': updated, 'references': [], 'files': []}
    if locations:
        plan['references'].append({'owner': 'Current scene', 'locations': locations, 'writable': True})
    paths = _source_paths(repository)
    total = 0
    for path, mode in paths:
        if not path.is_file():
            continue
        raw = _read_bytes(path)
        if not raw:
            raise ValueError('Reference document is empty or exceeds four MiB: ' + str(path))
        total += len(raw)
        if total > 16 * 1024 * 1024:
            raise ValueError('Reference scan exceeds sixteen MiB')
        document = json.loads(raw)
        rewritten, locations = (rewrite_preset(document, asset['path'], replacement, repository.root) if mode == 'preset'
                                else rewrite_scene(document, asset['path'], replacement, path.parent))
        if not locations:
            continue
        writable = not protected(path, repository.root)
        plan['references'].append({'owner': str(path), 'locations': locations, 'writable': writable})
        if writable:
            plan['files'].append({'path': str(path), 'before': raw,
                                  'after': json.dumps(rewritten, ensure_ascii=False, allow_nan=False).encode('utf-8')})
    return plan


def _source_paths(repository: AssetRepository) -> list[tuple[Path, str]]:
    paths = []
    directory = repository.root / 'presets'
    if directory.is_dir():
        for path in directory.glob('*.json'):
            paths.append((path, 'preset'))
            if len(paths) > 200:
                raise ValueError('Reference scan supports at most 200 presets')
    known = {path.resolve() for path, _mode in paths}
    for entry in repository.assets.values():
        path = Path(entry['path'])
        if entry['kind'] == 'scene' and path.suffix.lower() == '.json' and path.resolve() not in known:
            known.add(path.resolve())
            paths.append((path, 'scene'))
    return paths


def list_references(repository: AssetRepository, identity: str, scene: dict) -> list[dict]:
    """Scan missing assets too without requiring their old bytes to be available."""
    entry = repository.assets[identity]
    # A reference-only scan must not thumbnail or validate a missing replacement.
    return _reference_only(repository, entry['path'], scene)


def _reference_only(repository: AssetRepository, path: str, scene: dict) -> list[dict]:
    _rewritten, locations = rewrite_scene(scene, path, path, repository.root)
    result = [{'owner': 'Current scene', 'locations': locations, 'writable': True}] if locations else []
    total = 0
    for source, mode in _source_paths(repository):
        if not source.is_file():
            continue
        document = read_json(source)
        total += source.stat().st_size
        if total > 16 * 1024 * 1024:
            raise ValueError('Reference scan exceeds sixteen MiB')
        _rewritten, locations = (rewrite_preset(document, path, path, repository.root) if mode == 'preset'
                                else rewrite_scene(document, path, path, source.parent))
        if locations:
            result.append({'owner': str(source), 'locations': locations, 'writable': not protected(source, repository.root)})
    return result


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_bytes(path: Path) -> bytes:
    if not path.exists():
        return b''
    if path.is_symlink():
        raise ValueError('Reference document cannot be linked')
    with path.open('rb') as stream:
        data = stream.read(4 * 1024 * 1024 + 1)
    if len(data) > 4 * 1024 * 1024:
        raise ValueError('Reference document exceeds four MiB')
    return data


def commit_relink(repository: AssetRepository, plan: dict, *, writer=atomic_write, cancelled=None) -> None:
    """Persist a rollback journal before replacing any reviewed document; reject changed files."""
    identity = plan['identity']
    if repository.assets[identity]['path'] != plan['old']:
        raise ValueError('Asset path changed after review')
    kind, _image = inspect_asset(plan['new'])
    if kind != repository.assets[identity]['kind']:
        raise ValueError('Replacement changed after review')
    after = deepcopy(repository.assets)
    after[identity]['path'] = plan['new']
    files = list(plan['files'])
    original = _read_bytes(repository.path)
    files.append({'path': str(repository.path), 'before': original, 'after': repository.encode(after)})
    if len(files) > 50 or sum(len(record['before']) + len(record['after']) for record in files) > 16 * 1024 * 1024:
        raise ValueError('Repair exceeds fifty files/sixteen MiB; split the operation')
    for record in files:
        path = Path(record['path'])
        if path != repository.path and protected(path, repository.root):
            raise ValueError('Repair target is read-only')
        if _read_bytes(path) != record['before']:
            raise ValueError('Reference changed after review: ' + str(path))
        if path != repository.path:
            _check_plan_file(repository, plan, record)
    journal = repository.root / '.asset-relink.json'
    payload = {'version': 1, 'files': [dict(path=record['path'], before=base64.b64encode(record['before']).decode('ascii'),
                                          after_hash=_digest(record['after'])) for record in files]}
    atomic_write(journal, json.dumps(payload).encode('utf-8'))
    try:
        for record in files:
            if cancelled is not None and cancelled.is_set():
                raise ValueError('Asset repair cancelled')
            path = Path(record['path'])
            if _read_bytes(path) != record['before']:
                raise ValueError('Reference changed during repair')
            writer(path, record['after'])
    except BaseException:
        recover_relink(repository.root)
        raise
    journal.unlink()
    repository.assets = after


def _check_plan_file(repository: AssetRepository, plan: dict, record: dict) -> None:
    path, before = Path(record['path']), json.loads(record['before'])
    if path.parent == repository.root / 'presets':
        expected, locations = rewrite_preset(before, plan['old'], plan['new'], repository.root)
    elif any(entry['kind'] == 'scene' and Path(entry['path']) == path for entry in repository.assets.values()):
        expected, locations = rewrite_scene(before, plan['old'], plan['new'], path.parent)
    else:
        raise ValueError('Repair target is not an active preset or registered scene')
    if not locations or json.loads(record['after']) != expected:
        raise ValueError('Repair candidate changes fields outside the reviewed asset references')


def recover_relink(root: Path) -> None:
    """Roll back an interrupted transaction only when targets still match known old/new bytes."""
    journal = root / '.asset-relink.json'
    if not journal.exists():
        return
    document = read_json(journal, 24 * 1024 * 1024)
    if set(document) != {'version', 'files'} or document['version'] != 1 or not isinstance(document['files'], list) or len(document['files']) > 50:
        raise ValueError('Invalid asset repair journal')
    records, total = [], 0
    for record in document['files']:
        if not isinstance(record, dict) or set(record) != {'path', 'before', 'after_hash'}:
            raise ValueError('Invalid asset repair journal record')
        if not isinstance(record['after_hash'], str) or not re.fullmatch('[0-9a-f]{64}', record['after_hash']):
            raise ValueError('Invalid asset repair journal hash')
        path = Path(record['path'])
        if path.suffix.lower() != '.json' or protected(path, root):
            raise ValueError('Asset repair journal target is outside writable workspace JSON')
        before = base64.b64decode(record['before'], validate=True)
        total += len(before)
        if total > 16 * 1024 * 1024 or len(before) > 4 * 1024 * 1024:
            raise ValueError('Asset repair journal exceeds its byte limit')
        current = _read_bytes(path)
        if _digest(current) not in (_digest(before), record['after_hash']):
            raise ValueError('Repair recovery conflict; retain journal and changed file: ' + str(path))
        records.append((path, before))
    _check_recovery_targets(root, records)
    for path, before in reversed(records):
        if before:
            atomic_write(path, before)
        else:
            path.unlink(missing_ok=True)
    journal.unlink()


def _check_recovery_targets(root: Path, records: list) -> None:
    catalog = root / 'asset-library.json'
    originals = [raw for path, raw in records if path == catalog]
    if len(originals) != 1 or not originals[0]:
        raise ValueError('Repair journal requires exactly one prior catalog')
    document = json.loads(originals[0])
    if set(document) != {'version', 'assets'} or type(document['version']) is not int or document['version'] != 1:
        raise ValueError('Invalid prior catalog in repair journal')
    assets = checked_assets(document['assets'])
    scenes = {Path(entry['path']).absolute() for entry in assets.values() if entry['kind'] == 'scene'}
    seen = set()
    for path, raw in records:
        if path in seen or not path.is_absolute():
            raise ValueError('Duplicate/relative repair journal target')
        seen.add(path)
        if path == catalog:
            continue
        before = json.loads(raw)
        if path.parent == root / 'presets':
            checked_state(before)
        elif path in scenes and path.suffix.lower() == '.json':
            validate_geometry(normalize_scene(before, path.parent))
        else:
            raise ValueError('Journal target was not a registered scene or active local preset')
