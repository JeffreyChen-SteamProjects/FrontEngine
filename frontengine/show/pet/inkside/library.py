"""Install the built-in INKSIDE characters and their wardrobe into a pet asset library.

The assets are generated into a temporary folder and then go through the same
validated installation as any downloaded asset, so the wardrobe treats them
exactly like third-party packs. Versions already installed are left untouched.
"""
from __future__ import annotations

from pathlib import Path
import tempfile
from threading import Event
from typing import Callable

from frontengine.show.pet.inkside.assemble import build_character, build_garment, garment_identifier
from frontengine.show.pet.inkside.cast import TEMPLATES
from frontengine.show.pet.inkside.garments import GARMENTS

VERSION = '1'


def builtin_names() -> list[tuple[str, str]]:
    return [(template.ident, template.name) for template in TEMPLATES]


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
    with tempfile.TemporaryDirectory(prefix='frontengine-inkside-') as staging:
        sources = []
        for index, (ident, build) in enumerate(missing):
            if cancel.is_set():
                raise InterruptedError('Asset installation cancelled')
            sources.append(build(Path(staging) / ident))
            if progress is not None:
                progress(index + 1, 2 * len(missing))
        library.install_many(sources, cancel=cancel)
    return len(missing)
