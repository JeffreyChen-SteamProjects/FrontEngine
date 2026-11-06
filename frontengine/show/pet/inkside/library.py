"""Install the built-in INKSIDE characters and their wardrobe into a pet asset library.

The assets are generated into a temporary folder and then go through the same
validated installation as any downloaded asset, so the wardrobe treats them
exactly like third-party packs. Versions already installed are left untouched;
a pet still wearing an older built-in version is moved to the current one by an
explicit, checked appearance change (``upgrade_builtin``), never by substitution.
"""
from __future__ import annotations

from pathlib import Path
import tempfile
from threading import Event
from typing import Callable

from frontengine.show.pet.inkside.assemble import build_character, build_garment, garment_identifier
from frontengine.show.pet.inkside.builder import ASSET_VERSION
from frontengine.show.pet.inkside.cast import TEMPLATES
from frontengine.show.pet.inkside.garments import GARMENTS

VERSION = ASSET_VERSION


def builtin_names() -> list[tuple[str, str]]:
    return [(template.ident, template.name) for template in TEMPLATES]


def builtin_identifiers() -> frozenset[str]:
    """Every built-in character and wardrobe piece identifier."""
    identifiers = {template.ident for template in TEMPLATES}
    identifiers.update(garment_identifier(garment, template) for template in TEMPLATES for garment in GARMENTS)
    return frozenset(identifiers)


def _older(reference) -> bool:
    if not isinstance(reference, dict) or reference.get('id') not in builtin_identifiers():
        return False
    version = reference.get('version')
    return isinstance(version, str) and version.isdigit() and int(version) < int(VERSION)


def upgrade_builtin(appearance: dict) -> dict | None:
    """The appearance with older built-in character and garment references at the current version.

    None when nothing refers to an older built-in version. Colours and part choices are kept;
    the result is still validated by the caller like any wardrobe candidate.
    """
    character = appearance.get('character')
    equipped = appearance.get('equipped') or {}
    colors = appearance.get('colors') or {}
    if not _older(character) and not any(_older(reference) for reference in equipped.values())             and not any(_older(_color_reference(key)) for key in colors):
        return None
    def current(reference):
        return {**reference, 'version': VERSION} if _older(reference) else reference
    def color_key(key):                     # colour overrides are keyed by exact "id@version"
        reference = _color_reference(key)
        return f"{reference['id']}@{VERSION}" if _older(reference) else key
    upgraded = {**appearance, 'character': current(character),
                'equipped': {slot: current(reference) for slot, reference in equipped.items()}}
    if 'colors' in appearance:
        upgraded['colors'] = {color_key(key): value for key, value in colors.items()}
    return upgraded


def _color_reference(key) -> dict | None:
    if not isinstance(key, str) or key.count('@') != 1:
        return None
    identifier, version = key.split('@')
    return {'id': identifier, 'version': version}


def _template(identifier: str):
    for template in TEMPLATES:
        if template.ident == identifier:
            return template
    raise ValueError(f'Unknown built-in character: {identifier}')


def install_builtin(library, identifier: str, cancel: Event | None = None,
                    progress: Callable[[int, int], None] | None = None) -> int:
    """Install one character and every wardrobe piece fitted to its body; return how many were new."""
    template = _template(identifier)
    cancel = cancel or Event()
    wanted = [(template.ident, lambda folder: build_character(template, folder))]
    wanted += [(garment_identifier(garment, template),
                lambda folder, garment=garment: build_garment(garment, template, folder)) for garment in GARMENTS]
    missing = [(ident, build) for ident, build in wanted if not library.is_installed(ident, VERSION)]
    if progress is not None:
        progress(0, 2 * len(missing))
    with tempfile.TemporaryDirectory(prefix='frontengine-inkside-') as staging:
        sources = []
        for index, (ident, build) in enumerate(missing):
            if cancel.is_set():
                raise InterruptedError('Asset installation cancelled')
            # Resolved: layered assets reject symlinked ancestors, and macOS temp is /var -> /private/var.
            sources.append(build(Path(staging).resolve() / ident))
            if progress is not None:
                progress(index + 1, 2 * len(missing))
        def installed(done: int, total: int) -> None:
            if progress is not None:
                progress(len(missing) + done, len(missing) + total)
        library.install_many(sources, cancel=cancel, progress=installed)
    return len(missing)
