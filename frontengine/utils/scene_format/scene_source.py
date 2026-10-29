"""Read a bounded scene without modifying GUI state or global settings."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import tempfile

from frontengine.utils.imervue.puppet_asset import validate_puppet
from frontengine.utils.scene_format.scene_editor_document import validate_geometry
from frontengine.utils.scene_format.scene_package import load_package
from frontengine.utils.scene_format.scene_3d_document import SceneDocument, read_scene_document


@dataclass
class PreparedScene:
    """Own extracted assets until adoption; rejected results must be closed."""

    entries: dict
    lease: tempfile.TemporaryDirectory | None = None
    document: SceneDocument | None = None
    models: dict | None = None

    def __post_init__(self):
        self.document = read_scene_document(self.document if self.document is not None else self.entries)
        self.entries = self.document.entries

    def prepare(self):
        self.document = read_scene_document(self.document)
        self.document.entries = validate_geometry(self.document.entries)
        self.entries = self.document.entries
        if self.document.mode == '3d':
            from frontengine.show.scene.runtime3d import prepare_models
            self.models = prepare_models(self.document)
        return self

    def close(self) -> None:
        """Release extraction once no preview or playback reads these paths."""
        if self.lease is not None:
            from .scene_resource_reads import release_scene_lease
            release_scene_lease(self.lease)
            self.lease = None


def read_scene_source(path: str | Path) -> PreparedScene:
    """Read JSON, .fescene or .puppet with no QWidget construction."""
    source = Path(path)
    if not source.is_file() or source.suffix.lower() not in ('.json', '.fescene', '.puppet'):
        raise ValueError('Choose an existing JSON, .fescene or .puppet scene')
    prepared = PreparedScene({})
    try:
        if source.suffix.lower() == '.fescene':
            data, prepared.lease = load_package(source)
            prepared.document = read_scene_document(data)
            prepared.entries = prepared.document.entries
        elif source.suffix.lower() == '.puppet':
            validate_puppet(source)
            prepared.entries = {'puppet': {'type': 'PUPPET', 'file_path': str(source.resolve()), 'opacity': 100}}
            prepared.document = SceneDocument(prepared.entries)
        else:
            with source.open('rb') as stream:
                data = stream.read(8 * 1024 * 1024 + 1)
            if len(data) > 8 * 1024 * 1024:
                raise ValueError('Scene JSON exceeds the size limit')
            prepared.document = read_scene_document(json.loads(data.decode('utf-8-sig')), source.parent)
            prepared.entries = prepared.document.entries
        if len(prepared.entries) > 256:
            raise ValueError('Automated scenes support at most 256 layers')
        return prepared.prepare()
    except (OSError, ValueError, RecursionError):
        prepared.close()
        raise
