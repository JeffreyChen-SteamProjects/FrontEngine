"""Read a bounded scene without modifying GUI state or global settings."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import tempfile

from frontengine.utils.imervue.puppet_asset import validate_puppet
from frontengine.utils.scene_format.scene_document import normalize_scene
from frontengine.utils.scene_format.scene_editor_document import validate_geometry
from frontengine.utils.scene_format.scene_package import load_package


@dataclass
class PreparedScene:
    """Own extracted assets until adoption; rejected results must be closed."""

    entries: dict
    lease: tempfile.TemporaryDirectory | None = None

    def close(self) -> None:
        """Release extraction once no preview or playback reads these paths."""
        if self.lease is not None:
            self.lease.cleanup()
            self.lease = None


def read_scene_source(path: str | Path) -> PreparedScene:
    """Read JSON, .fescene or .puppet with no QWidget construction."""
    source = Path(path)
    if not source.is_file() or source.suffix.lower() not in ('.json', '.fescene', '.puppet'):
        raise ValueError('Choose an existing JSON, .fescene or .puppet scene')
    prepared = PreparedScene({})
    try:
        if source.suffix.lower() == '.fescene':
            prepared.entries, prepared.lease = load_package(source)
        elif source.suffix.lower() == '.puppet':
            validate_puppet(source)
            prepared.entries = {'puppet': {'type': 'PUPPET', 'file_path': str(source.resolve()), 'opacity': 100}}
        else:
            with source.open('rb') as stream:
                data = stream.read(8 * 1024 * 1024 + 1)
            if len(data) > 8 * 1024 * 1024:
                raise ValueError('Scene JSON exceeds the size limit')
            prepared.entries = normalize_scene(json.loads(data.decode('utf-8-sig')), source.parent)
        if len(prepared.entries) > 256:
            raise ValueError('Automated scenes support at most 256 layers')
        prepared.entries = validate_geometry(prepared.entries)
        return prepared
    except (OSError, ValueError, RecursionError):
        prepared.close()
        raise
