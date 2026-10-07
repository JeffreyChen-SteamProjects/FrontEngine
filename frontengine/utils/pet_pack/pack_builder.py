"""Validate selected sprite actions and atomically export a portable folder."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile
from threading import Event

from PySide6.QtGui import QImageReader

STATES = ('walk', 'idle', 'sleep', 'climb', 'fall', 'drag')
ALIASES = (('walk', 'run', 'move'), ('idle', 'sit', 'stand'), ('sleep', 'zzz', 'rest'),
           ('climb', 'grab', 'wall'), ('fall', 'jump'), ('drag', 'pinch', 'grabbed', 'held'))
EXTENSIONS = ('.gif', '.webp', '.png', '.jpg', '.jpeg')
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_PACK_BYTES = 256 * 1024 * 1024


@dataclass(frozen=True)
class PackDraft:
    """Only selected sprite files and bounded size/movement traits are exported."""

    actions: dict[str, str]
    name: str = 'Sprite pet'
    size: int = 128
    speed: int = 3


def validate_sprite(path: str | Path) -> Path:
    """Inspect format/dimensions before starting a QMovie or copying a resource."""
    source = Path(path)
    if source.suffix.lower() not in EXTENSIONS or not source.is_file() or source.is_symlink():
        raise ValueError('Choose an existing PNG/JPEG/GIF/WebP sprite, not a .puppet file')
    if not 0 < source.stat().st_size <= MAX_FILE_BYTES:
        raise ValueError('A sprite file must be within 64 MiB')
    reader = QImageReader(str(source))
    size = reader.size()
    if not reader.canRead() or not 0 < size.width() * size.height() <= 16_777_216:
        raise ValueError('Sprite format is invalid or dimensions exceed 16 megapixels')
    return source.resolve()


def validate_draft(draft: PackDraft) -> PackDraft:
    """Validate all choices; missing optional actions use the existing loader fallback."""
    if not isinstance(draft.name, str) or not 1 <= len(draft.name.strip()) <= 80:
        raise ValueError('Pet pack name must contain 1–80 characters')
    if type(draft.size) is not int or not 16 <= draft.size <= 512:
        raise ValueError('Pet pack size must be within 16–512 pixels')
    if type(draft.speed) is not int or not 1 <= draft.speed <= 10:
        raise ValueError('Pet pack movement speed must be within 1–10')
    if not isinstance(draft.actions, dict) or not draft.actions or set(draft.actions) - set(STATES):
        raise ValueError('Choose at least one supported sprite action')
    actions = {state: str(validate_sprite(path)) for state, path in draft.actions.items()}
    if sum(Path(path).stat().st_size for path in actions.values()) > MAX_PACK_BYTES:
        raise ValueError('Pet pack resources exceed 256 MiB')
    return PackDraft(actions, draft.name.strip(), draft.size, draft.speed)


def missing_actions(draft: PackDraft) -> list[str]:
    """Return explicit gaps; no assets are invented to fill missing animations."""
    return [state for state in STATES if state not in draft.actions]


def load_pack(folder: str | Path, *, cancel: Event | None = None) -> PackDraft:
    """Import legacy action aliases and the supported bounded pet.json traits."""
    root = Path(folder)
    if not root.is_dir() or root.is_symlink():
        raise ValueError('Choose a regular sprite-pack folder')
    files = []
    for index, path in enumerate(root.iterdir()):
        if cancel is not None and cancel.is_set():
            raise InterruptedError('Pet pack import cancelled')
        if index >= 4096:
            raise ValueError('Sprite-pack folder exceeds 4096 entries')
        if path.is_file() and path.suffix.lower() in EXTENSIONS:
            files.append(path)
    by_stem = {path.stem.lower(): path for path in sorted(files)}
    actions = {}
    for state, aliases in zip(STATES, ALIASES):
        for alias in aliases:
            if alias in by_stem:
                actions[state] = str(by_stem[alias])
                break
    manifest = root / 'pet.json'
    metadata = {}
    if manifest.exists():
        if manifest.is_symlink():
            raise ValueError('Pet manifest must be a regular file')
        with manifest.open('rb') as stream:
            data = stream.read(65537)
        if len(data) > 65536:
            raise ValueError('Pet manifest exceeds 64 KiB')
        metadata = json.loads(data.decode('utf-8-sig'))
        if not isinstance(metadata, dict):
            raise ValueError('Pet manifest must be an object')
    return validate_draft(PackDraft(actions, metadata.get('name', root.name),
                                    metadata.get('size', 128), metadata.get('speed', 3)))


def export_pack(draft: PackDraft, destination: str | Path, *, cancel: Event | None = None) -> str:
    """Copy selected resources into a new folder; cancellation never overwrites it."""
    draft = validate_draft(draft)
    target = Path(destination).absolute()
    if target.exists() or target.is_symlink() or not target.parent.is_dir():
        raise ValueError('Export requires a new folder inside an existing parent directory')
    cancel = cancel or Event()
    with tempfile.TemporaryDirectory(prefix='.frontengine-pet-', dir=target.parent) as directory:
        staging = Path(directory).resolve()
        if not staging.is_relative_to(target.parent.resolve()):
            raise ValueError('Pet pack staging directory is outside its destination parent')
        total = 0
        for state, filename in draft.actions.items():
            source = Path(filename)
            copied = staging / (state + source.suffix.lower())
            total += _copy_sprite(source, copied, cancel)
            if total > MAX_PACK_BYTES:
                raise ValueError('Pet pack grew beyond the 256 MiB limit during export')
            validate_sprite(copied)
        metadata = {'name': draft.name, 'size': draft.size, 'speed': draft.speed}
        (staging / 'pet.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
        if cancel.is_set():
            raise InterruptedError('Pet pack export cancelled')
        if target.exists() or target.is_symlink():
            raise ValueError('Export folder already exists')
        os.rename(staging, target)
    return str(target)


def _copy_sprite(source: Path, target: Path, cancel: Event) -> int:
    copied = 0
    with source.open('rb') as input_stream, target.open('xb') as output_stream:
        while True:
            if cancel.is_set():
                raise InterruptedError('Pet pack export cancelled')
            chunk = input_stream.read(1024 * 1024)
            if not chunk:
                break
            copied += len(chunk)
            if copied > MAX_FILE_BYTES:
                raise ValueError('Sprite grew beyond the 64 MiB limit during export')
            output_stream.write(chunk)
        output_stream.flush()
        os.fsync(output_stream.fileno())
    return copied
