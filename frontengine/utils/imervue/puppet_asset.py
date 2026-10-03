"""Check archive boundaries before loading any optional puppet runtime."""
from __future__ import annotations

import json
import math
import stat
import zipfile
from pathlib import Path, PurePosixPath

MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_JSON_BYTES = 8 * 1024 * 1024
MEDIA_TYPE = 'application/vnd.imervue.puppet+zip'


def checked_members(archive: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    entries = archive.infolist()
    if len(entries) > 4096 or sum(item.file_size for item in entries) > MAX_ARCHIVE_BYTES:
        raise ValueError('Archive exceeds its resource limit')
    members = {}
    for item in entries:
        name = item.filename
        path = PurePosixPath(name)
        if (not name or '\\' in name or ':' in name or path.is_absolute()
                or '..' in path.parts or '\x00' in name
                or stat.S_ISLNK(item.external_attr >> 16)):
            raise ValueError(f'Unsafe archive path: {name!r}')
        if name in members:
            raise ValueError(f'Duplicate archive path: {name}')
        members[name] = item
    return members


def read_json_member(archive: zipfile.ZipFile, name: str) -> dict:
    try:
        info = archive.getinfo(name)
    except KeyError as error:
        raise ValueError(f'Missing archive member: {name}') from error
    if info.file_size > MAX_JSON_BYTES:
        raise ValueError(f'JSON member exceeds its resource limit: {name}')
    value = json.loads(archive.read(name))
    if not isinstance(value, dict):
        raise ValueError(f'{name} must be a JSON object')
    return value


def validate_puppet(path: str | Path) -> dict:
    try:
        with zipfile.ZipFile(path) as archive:
            members = checked_members(archive)
            if 'mimetype' in members:
                if members['mimetype'].file_size > 128 or archive.read('mimetype').decode('ascii') != MEDIA_TYPE:
                    raise ValueError('Unsupported puppet media type')
            raw = read_json_member(archive, 'puppet.json')
            _validate_manifest(raw, members)
            return raw
    except (zipfile.BadZipFile, UnicodeError, KeyError) as error:
        raise ValueError(f'Invalid puppet archive: {error}') from error


def _validate_manifest(raw: dict, members: dict) -> None:
    if type(raw.get('version')) is not int or raw['version'] != 1:
        raise ValueError('Unsupported puppet version; expected v1')
    size = raw.get('size')
    if not isinstance(size, list) or len(size) != 2 or any(type(v) is not int or not 1 <= v <= 16384 for v in size):
        raise ValueError('Invalid puppet canvas size')
    for name in ('drawables', 'deformers', 'parameters'):
        if not isinstance(raw.get(name), list) or any(not isinstance(v, dict) for v in raw[name]):
            raise ValueError(f'Invalid puppet {name}')
    for drawable in raw['drawables']:
        texture = drawable.get('texture')
        if not isinstance(texture, str) or not texture.startswith('textures/') or texture not in members:
            raise ValueError('Missing or invalid puppet texture')
    for collection, folder in (('motions', 'motions'), ('expressions', 'expressions')):
        values = raw.get(collection, [])
        if not isinstance(values, list):
            raise ValueError(f'Invalid puppet {collection}')
        for name in values:
            if not isinstance(name, str) or '/' in name or '\\' in name or f'{folder}/{name}.json' not in members:
                raise ValueError(f'Missing or invalid puppet {collection} reference')
    if raw.get('physics') is not None and (not isinstance(raw['physics'], str) or raw['physics'] not in members):
        raise ValueError('Missing puppet physics reference')


def finite_parameters(values: object) -> dict[str, float]:
    if not isinstance(values, dict):
        raise ValueError('Puppet parameters must be an object')
    result = {}
    for key, value in values.items():
        if not isinstance(key, str) or type(value) not in (float, int) or not math.isfinite(value):
            raise ValueError('Puppet parameters must be finite numbers')
        result[key] = float(value)
    return result
