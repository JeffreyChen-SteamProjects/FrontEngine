"""Render the built-in characters' card icons from their layered rig.

    py tools/inkside_icons.py

Builds each character in a temporary folder, renders the first sitting frame through the
layered renderer and writes ``frontengine/show/pet/inkside/icons/<id>.png`` (shipped as package
data). Rerun after changing a character's drawing or the sitting pose.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ICON_SIZE = 112


def main() -> None:
    sys.path.insert(0, str(REPO))            # this checkout, not an installed frontengine
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    from frontengine.show.pet.inkside.assemble import build_character
    from frontengine.show.pet.inkside.cast import TEMPLATES
    from frontengine.show.pet.layered_renderer import LayeredRenderer
    from frontengine.utils.pet_pack.layered import load_layered_asset
    app = QApplication.instance() or QApplication([])
    folder = REPO / 'frontengine/show/pet/inkside/icons'
    folder.mkdir(parents=True, exist_ok=True)
    for template in TEMPLATES:
        with tempfile.TemporaryDirectory(prefix='frontengine-icon-') as root:
            asset = load_layered_asset(build_character(template, Path(root).resolve() / template.ident))
            frame = LayeredRenderer(asset).render('sit', 0)
        icon = frame.scaled(ICON_SIZE, ICON_SIZE, Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation)
        target = folder / f'{template.ident}.png'
        if not icon.save(str(target), 'PNG'):
            raise OSError(f'Could not write {target}')
        print(target)
    del app


if __name__ == '__main__':
    main()
