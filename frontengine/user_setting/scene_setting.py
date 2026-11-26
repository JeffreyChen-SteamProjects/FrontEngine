import os
import json
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import QObject, QRunnable, Qt, Signal
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from shiboken6 import isValid

from frontengine.ui.dialog.choose_file_dialog import choose_file
from frontengine.utils.json.json_repository import JsonRepository
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.work_lifetime import captured_lifetime
from frontengine.utils.scene_format.scene_package import load_package, save_package
from frontengine.utils.scene_format.scene_3d_document import SceneDocument, read_scene_document

scene_json: Dict[str, Any] = {}
_package_leases: list = []
_writes: set = set()          # what saves under way report through, kept until they have
_scene_document = SceneDocument()


def current_scene_document() -> SceneDocument:
    document = _scene_document.copy()
    document.entries = dict(scene_json)
    return document


def adopt_scene_document(document, lease=None) -> None:
    global _scene_document
    _scene_document = read_scene_document(document)
    if lease is not None:
        _package_leases.append(lease)
    scene_json.clear()
    scene_json.update(_scene_document.entries)


def adopt_scene_entries(entries: dict, lease=None) -> None:
    """Apply worker-loaded scene data on the GUI thread and retain its extraction lease."""
    adopt_scene_document(entries, lease)


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
        entries = read_scene_document(json.loads(source.read_text(encoding='utf-8-sig')), source.parent)
    adopt_scene_document(entries)
    return scene_json


def release_scene_packages() -> None:
    from frontengine.utils.scene_format.scene_resource_reads import release_scene_lease
    for lease in _package_leases:
        release_scene_lease(lease)
    _package_leases.clear()


def choose_scene_file(trigger_ui: QWidget) -> Optional[str]:
    """Which scene file to open, or None; reading it is the caller's."""
    front_engine_logger.info("choose_scene_file")
    return choose_file(
        trigger_ui=trigger_ui,
        file_filter='Scene / Puppet (*.json *.fescene *.puppet)',
        extensions=['.json', '.fescene', '.puppet'],
        warning_message=language_wrapper.language_word_dict.get("scene_choose_message_box"),
    )


class _WriteSignals(QObject):
    finished = Signal(str)


class _SceneWrite(QRunnable):
    """Save a snapshot of the scene off the GUI thread: a package is compressed with all its media."""

    def __init__(self, document: SceneDocument, path: str) -> None:
        super().__init__()
        self.document, self.path, self.signals = document, path, _WriteSignals()

    def run(self) -> None:
        error = ''
        try:
            save_scene_document(self.document, self.path)
        except Exception as failure:  # any at all: unsaid, the user believes it was saved
            front_engine_logger.warning(f'[scene_setting] scene not saved: {failure!r}')
            error = str(failure) or type(failure).__name__
        self.signals.finished.emit(error)


def save_scene_document(document: SceneDocument, path: str) -> None:
    if Path(path).suffix.lower() == '.fescene':
        save_package(document, path)
    else:
        JsonRepository(path).save(document.envelope(Path(path).parent))


def write_scene_file(parent_qt_instance: QWidget,
                     file_filter: str = 'Scene package (*.fescene);;Scene JSON (*.json)') -> Optional[str]:
    file_path, _ = QFileDialog().getSaveFileName(
        parent=parent_qt_instance,
        dir=os.getcwd(),
        filter=file_filter,
    )

    if not file_path:
        return None

    job = _SceneWrite(current_scene_document(), file_path)

    def done(error: str) -> None:
        _writes.discard(job.signals)
        if error and isValid(parent_qt_instance):
            QMessageBox.critical(parent_qt_instance, 'Scene Error', error)

    job.signals.finished.connect(done, Qt.ConnectionType.QueuedConnection)
    _writes.add(job.signals)
    captured_lifetime(parent_qt_instance).submit(job)
    return file_path
