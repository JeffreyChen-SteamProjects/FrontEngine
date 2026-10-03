import os
import json
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtWidgets import QFileDialog, QWidget

from frontengine.ui.dialog.choose_file_dialog import choose_file
from frontengine.utils.json.json_repository import JsonRepository
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.scene_format.scene_document import normalize_scene, scene_envelope
from frontengine.utils.scene_format.scene_package import load_package, save_package

scene_json: Dict[str, Any] = {}
_package_leases: list = []


def load_scene_file(path: str | Path) -> dict:
    source = Path(path)
    if source.suffix.lower() == '.fescene':
        entries, lease = load_package(source)
        _package_leases.append(lease)
    elif source.suffix.lower() == '.puppet':
        from frontengine.utils.imervue.puppet_asset import validate_puppet
        validate_puppet(source)
        entries = {'puppet': {'type': 'PUPPET', 'file_path': str(source.resolve()), 'opacity': 100}}
    else:
        if source.stat().st_size > 8 * 1024 * 1024:
            raise ValueError('Scene JSON exceeds the size limit')
        entries = normalize_scene(json.loads(source.read_text(encoding='utf-8-sig')), source.parent)
    scene_json.clear()
    scene_json.update(entries)
    return entries


def release_scene_packages() -> None:
    for lease in _package_leases:
        lease.cleanup()
    _package_leases.clear()


def choose_scene_json(
    trigger_ui: QWidget,
    file_filter: str = 'Scene / Puppet (*.json *.fescene *.puppet)',
    extensions: Optional[list[str]] = None,
) -> Optional[str]:
    front_engine_logger.info("choose_scene_json")

    file_path = choose_file(
        trigger_ui=trigger_ui,
        file_filter=file_filter,
        extensions=extensions or ['.json', '.fescene', '.puppet'],
        warning_message=language_wrapper.language_word_dict.get("scene_choose_message_box"),
    )

    if not file_path:
        return None

    load_scene_file(file_path)
    return file_path


def write_scene_file(parent_qt_instance: QWidget,
                     file_filter: str = 'Scene package (*.fescene);;Scene JSON (*.json)') -> Optional[str]:
    file_path, _ = QFileDialog().getSaveFileName(
        parent=parent_qt_instance,
        dir=os.getcwd(),
        filter=file_filter,
    )

    if not file_path:
        return None

    if Path(file_path).suffix.lower() == '.fescene':
        save_package(scene_json, file_path)
    else:
        JsonRepository(file_path).save(scene_envelope(scene_json, Path(file_path).parent))
    return file_path
