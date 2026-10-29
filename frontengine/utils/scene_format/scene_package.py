"""Portable .fescene archive import/export with a caller-owned extraction lease."""
from __future__ import annotations

import json
import os
import tempfile
import zipfile
from pathlib import Path

from frontengine.utils.imervue.puppet_asset import MAX_ARCHIVE_BYTES, checked_members, read_json_member
from frontengine.utils.scene_format.scene_document import ASSET_FIELDS
from frontengine.utils.scene_format.scene_3d_document import read_scene_document


def save_package(entries: dict, destination: str | Path) -> str:
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    document = read_scene_document(entries)
    data = document.entries
    fd, temporary = tempfile.mkstemp(prefix='.scene-', suffix='.part', dir=target.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as archive:
            _write_assets(data, archive)
            archive.writestr('scene.json', json.dumps(document.envelope(), ensure_ascii=False, indent=2))
        with zipfile.ZipFile(temporary) as archive:
            if sum(info.file_size for info in archive.infolist()) > MAX_ARCHIVE_BYTES:
                raise ValueError('Archive exceeds its resource limit')
            checked_members(archive)
            read_json_member(archive, 'scene.json')
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return str(target)


def _write_assets(data: dict, archive: zipfile.ZipFile) -> None:
    copied = {}
    for entry in data.values():
        for field in ASSET_FIELDS:
            value = entry.get(field)
            if not value:
                continue
            original = Path(value)
            source = original.resolve()
            if not source.is_file() or original.is_symlink():
                raise ValueError(f'Scene asset is not a file: {value}')
            if source not in copied:
                name = f'assets/{len(copied):04d}/{source.name}'
                if entry.get('type') == 'MODEL' and field == 'file_path':
                    from frontengine.show.scene.model_asset import model_dependencies
                    directory = Path(name).parent
                    for resource in sorted(model_dependencies(source)):
                        resource_name = (directory / resource.relative_to(source.parent)).as_posix()
                        archive.write(resource, resource_name)
                else:
                    archive.write(source, name)
                copied[source] = name
            entry[field] = copied[source]


def load_package(path: str | Path) -> tuple[dict, tempfile.TemporaryDirectory]:
    lease = tempfile.TemporaryDirectory(prefix='frontengine-scene-')
    root = Path(lease.name).resolve()
    try:
        with zipfile.ZipFile(path) as archive:
            members = checked_members(archive)
            raw = read_json_member(archive, 'scene.json')
            document = read_scene_document(raw, root)
            entries = document.entries
            for entry in entries.values():
                for field in ASSET_FIELDS:
                    if not entry.get(field):
                        continue
                    resource = Path(entry[field])
                    if not resource.is_relative_to(root):
                        raise ValueError('Packaged scene asset is outside its package')
                    name = resource.relative_to(root).as_posix()
                    if name not in members or members[name].is_dir():
                        raise ValueError(f'Missing packaged scene resource: {name}')
            for name, info in members.items():
                if info.is_dir():
                    continue
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, target.open('wb') as output:
                    for block in iter(lambda: source.read(65536), b''):
                        output.write(block)
        for entry in entries.values():
            if entry.get('type') == 'MODEL':
                from frontengine.show.scene.model_asset import model_dependencies
                model_dependencies(entry['file_path'])
        return (document if document.mode == '3d' else entries), lease
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as error:
        lease.cleanup()
        raise ValueError(f'Invalid scene package: {error}') from error
    except BaseException:
        lease.cleanup()
        raise
