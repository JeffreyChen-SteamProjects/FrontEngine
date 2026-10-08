"""Bounded local catalog; tagging never copies or starts the selected resource."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from os.path import normcase
import re
from uuid import uuid4

from PySide6.QtGui import QImage

from frontengine.utils.asset_library.inspect import inspect_asset, read_json
from frontengine.utils.todo.repository import atomic_write


def checked_assets(value) -> dict:
    """Validate at most 200 paths and bounded tags before using saved catalog metadata."""
    if not isinstance(value, list) or len(value) > 200:
        raise ValueError('Asset library supports at most 200 entries')
    result, paths = {}, set()
    for entry in value:
        if not isinstance(entry, dict) or set(entry) != {'id', 'path', 'kind', 'tags', 'favorite'}:
            raise ValueError('Invalid asset catalog fields')
        if not isinstance(entry['id'], str) or not re.fullmatch('[0-9a-f]{32}', entry['id']) or entry['id'] in result:
            raise ValueError('Invalid asset identifier')
        if not isinstance(entry['path'], str) or len(entry['path']) > 4096 or not Path(entry['path']).is_absolute():
            raise ValueError('Asset path must be absolute and within 4096 characters')
        key = normcase(str(Path(entry['path']).absolute()))
        if key in paths or entry['kind'] not in ('image', 'gif', 'pet', 'puppet', 'scene') or type(entry['favorite']) is not bool:
            raise ValueError('Duplicate asset path or invalid kind/favorite')
        tags = entry['tags']
        if not isinstance(tags, list) or len(tags) > 32 or any(not isinstance(tag, str) or not tag.strip() or len(tag) > 40 for tag in tags):
            raise ValueError('Asset tags must contain up to 32 nonempty 40-character labels')
        result[entry['id']] = deepcopy(entry)
        paths.add(key)
    return result


class AssetRepository:
    """Store metadata independently from media and retain missing paths for explicit repair."""

    def __init__(self, root: str | Path, *, writer=atomic_write) -> None:
        self.root, self.writer = Path(root).absolute(), writer
        self.path = self.root / 'asset-library.json'
        self.assets = {}
        if self.path.exists():
            document = read_json(self.path, 1024 * 1024)
            if document.get('version') != 1 or type(document.get('version')) is not int or set(document) != {'version', 'assets'}:
                raise ValueError('Unsupported asset catalog version')
            self.assets = checked_assets(document['assets'])

    @staticmethod
    def encode(assets: dict) -> bytes:
        """Serialize only fully validated version-one catalog records."""
        normalized = checked_assets(list(assets.values()))
        data = json.dumps({'version': 1, 'assets': list(normalized.values())}, ensure_ascii=False).encode('utf-8')
        if len(data) > 1024 * 1024:
            raise ValueError('Asset catalog exceeds one MiB')
        return data

    def save(self, assets: dict) -> None:
        """Publish metadata only after atomic persistence succeeds."""
        self.writer(self.path, self.encode(assets))
        self.assets = deepcopy(assets)

    def add(self, path: str | Path) -> str:
        """Validate a user-selected asset; deduplicate paths without clearing tags/favorite."""
        source = str(Path(path).absolute())
        for entry in self.assets.values():
            if Path(entry['path']) == Path(source):
                return entry['id']
        kind, _image = inspect_asset(source)
        identity = uuid4().hex
        after = deepcopy(self.assets)
        after[identity] = dict(id=identity, path=source, kind=kind, tags=[], favorite=False)
        self.save(after)
        return identity

    def edit(self, identity: str, *, tags: list[str], favorite: bool) -> None:
        """Update only local organization metadata, never resource bytes."""
        after = deepcopy(self.assets)
        after[identity].update(tags=list(dict.fromkeys(tag.strip() for tag in tags)), favorite=favorite)
        self.save(after)

    def remove(self, identity: str) -> None:
        """Forget one catalog entry; do not delete its files or scene references."""
        after = deepcopy(self.assets)
        after.pop(identity, None)
        self.save(after)

    def entries(self, *, text: str = '', favorites: bool = False) -> list[dict]:
        """Generate bounded static thumbnails on the worker; missing entries stay searchable."""
        if not isinstance(text, str) or len(text) > 256 or type(favorites) is not bool:
            raise ValueError('Invalid asset search')
        result = []
        for entry in self.assets.values():
            haystack = entry['path'] + ' ' + entry['kind'] + ' ' + ' '.join(entry['tags'])
            if (favorites and not entry['favorite']) or text.casefold() not in haystack.casefold():
                continue
            image, error = QImage(), ''
            try:
                kind, image = inspect_asset(entry['path'])
                if kind != entry['kind']:
                    image, error = QImage(), 'Asset type changed; remove and register it again'
            except (OSError, ValueError, RuntimeError) as failure:
                error = str(failure)[:2000]
            result.append({**deepcopy(entry), 'thumbnail': image, 'error': error})
        return sorted(result, key=lambda entry: (not entry['favorite'], Path(entry['path']).name.casefold(), entry['id']))
