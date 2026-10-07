"""Fixed packaged scene acceptance; no executable test scripts or personal settings are loaded."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import tempfile
from typing import Callable

KINDS = {'IMAGE', 'GIF', 'TEXT', 'VIDEO', 'WEB', 'PUPPET', 'SOUND'}


def checked_fixtures(directory: Path) -> dict:
    """Require seven local, script-free fixture types before allocating native renderers."""
    from PySide6.QtCore import QUrl
    from frontengine.utils.scene_format.scene_document import normalize_scene
    source = directory / 'scene.json'
    if not source.is_file() or source.stat().st_size > 65536:
        raise ValueError('Missing or excessive fixture scene.json')
    entries = normalize_scene(json.loads(source.read_text(encoding='utf-8')), directory)
    if len(entries) != 7 or {entry.get('type') for entry in entries.values()} != KINDS:
        raise ValueError('Fixture scene must contain exactly one of each supported type')
    for entry in entries.values():
        if entry.get('script_path'):
            raise ValueError('Acceptance fixtures must not contain scripts')
        if entry.get('type') == 'WEB':
            url = QUrl(entry.get('url', ''))
            if not url.isLocalFile():
                raise ValueError('Acceptance web fixture must be local')
            _local_file(Path(url.toLocalFile()), directory)
        elif entry.get('file_path'):
            _local_file(Path(entry['file_path']), directory)
    return entries


def _local_file(path: Path, directory: Path) -> None:
    if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()) or not path.is_file():
        raise ValueError('Acceptance asset must be a file inside the fixture directory')


def wait_for(predicate: Callable[[], bool], *, milliseconds: int = 25000) -> None:
    """Process real native Qt events with a finite acceptance deadline."""
    from PySide6.QtTest import QTest
    for _ in range(milliseconds // 25):
        QTest.qWait(25)
        if predicate():
            return
    raise ValueError('Native scene acceptance timed out')


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def _ready(editor) -> bool:
    sources = editor.media_preview.sources
    if editor.media_preview.errors:
        raise ValueError(str(editor.media_preview.errors))
    if len(sources) != 4:
        return False
    if not all(_source_ready(source) for source in sources.values()):
        return False
    return all(item.image is not None and not item.image.isNull() if item.entry['type'] == 'IMAGE'
               else item.movie.isValid() and not item.movie.currentImage().isNull()
               for item in editor.canvas.items() if item.entry['type'] in ('IMAGE', 'GIF'))


def _source_ready(source) -> bool:
    kind = source.entry['type']
    if kind == 'SOUND':
        return source.media_player.duration() > 0
    if source.frame.isNull():
        return False
    if kind == 'WEB':
        return source.frame.pixelColor(70, 40).name() == '#13579b'
    if kind == 'VIDEO':
        return source.frame.pixelColor(70, 40).red() > 190
    return True


def _inspect_preview(editor, report: Path) -> dict:
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QImage, QPainter, QColor
    image = QImage(480, 480, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor('transparent'))
    painter = QPainter(image)
    editor.canvas.render(painter, QRectF(0, 0, 480, 480), QRectF(0, 0, 480, 480))
    painter.end()
    _require(image.pixelColor(3, 3) == QColor('blue'), 'Image layer must cover the video at z=20')
    _require(image.pixelColor(70, 40).red() > 190, 'Native video must decode')
    _require(image.pixelColor(230, 40).name() == '#13579b', 'Local web page must render')
    _require(image.save(str(report / 'composition.png')), 'Native scene acceptance failed')
    _require(editor.grab().save(str(report / 'editor.png')), 'Native scene acceptance failed')
    sources = editor.media_preview.sources
    puppet = next(source for source in sources.values() if source.entry['type'] == 'PUPPET')
    _require(puppet.host.canvas.isValid(), 'Native scene acceptance failed')
    _require(any(puppet.frame.pixelColor(x, y).alpha() for x in range(0, puppet.frame.width(), 10)
               for y in range(0, puppet.frame.height(), 10)), 'Puppet must render into its own FBO')
    _require(all(source.audio_output.isMuted() for source in sources.values() if source.audio_output), 'Native scene acceptance failed')
    return {'types': sorted(KINDS), 'image_video_web_pixels': True, 'puppet_native_fbo': True,
            'muted_preview': True, 'qt_screen_dpr': editor.screen().devicePixelRatio()}


def _interaction_and_history(editor) -> None:
    from PySide6.QtTest import QTest
    web = next(source for source in editor.media_preview.sources.values() if source.entry['type'] == 'WEB')
    editor.media_preview.interact('web')
    result = []
    web.host.page().runJavaScript("document.getElementById('input').value='Packaged'; document.getElementById('input').value", result.append)
    wait_for(lambda: result == ['Packaged'])
    movie = next(item.movie for item in editor.canvas.items() if item.entry['type'] == 'GIF')
    frame = movie.currentFrameNumber()
    wait_for(lambda: movie.currentFrameNumber() != frame)
    sources = dict(editor.media_preview.sources)
    editor.document.update('image', {'x': 40})
    _require(editor.document.entries['image']['x'] == 40, 'Native scene acceptance failed')
    editor.document.undo.undo()
    _require(editor.document.entries['image'].get('x', 0) == 0, 'Native scene acceptance failed')
    editor.document.undo.redo()
    _require(editor.document.entries['image']['x'] == 40, 'Native scene acceptance failed')
    editor.document.undo.undo()
    _require(editor.media_preview.sources == sources, 'Geometry edits must retain native media owners')
    editor.hide()
    _require(all(not source.active and not source.timer.isActive() for source in sources.values()), 'Native scene acceptance failed')
    editor.show()
    QTest.qWait(150)
    _require(all(source.active for source in sources.values()), 'Native scene acceptance failed')


def verify_scene(fixtures: Path, report: Path) -> dict:
    """Exercise the compiled editor, exports and lease ordering with our own native widgets."""
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QApplication
    from shiboken6 import isValid
    from frontengine.ui.page.scene_setting.scene_setting_ui import SceneSettingUI
    from frontengine.user_setting.scene_setting import load_scene_file, release_scene_packages
    from frontengine.utils.scene_format.scene_package import save_package
    from frontengine.utils.scene_format.scene_document import scene_envelope
    entries = checked_fixtures(fixtures)
    _require(QApplication.platformName() not in ('offscreen', 'minimal'), 'Use a real native Qt platform')
    page, sources = SceneSettingUI(), []
    try:
        page.resize(1080, 780)
        page.setWindowTitle('FrontEngine packaged scene acceptance')
        page.show()
        editor = page.visual_editor
        editor.load_entries(load_scene_file(fixtures / 'scene.json'))
        editor.media_enabled.setChecked(True)
        wait_for(lambda: _ready(editor))
        result = _inspect_preview(editor, report)
        _interaction_and_history(editor)
        _require(len(editor.document.entries) == len(entries) == 7, 'Native scene acceptance failed')
        save_package(editor.document.entries, report / 'all-types.fescene')
        (report / 'all-types.json').write_text(json.dumps(scene_envelope(editor.document.entries)), encoding='utf-8')
        _require(load_scene_file(report / 'all-types.json') == editor.document.entries, 'Native scene acceptance failed')
        packaged = load_scene_file(report / 'all-types.fescene')
        _require({value['type'] for value in packaged.values()} == KINDS, 'Native scene acceptance failed')
        editor.load_entries(packaged)
        wait_for(lambda: _ready(editor))
        sources = list(editor.media_preview.sources.values())
        page.close()
        _require(not isValid(editor) or not editor.media_preview.sources, 'Native scene acceptance failed')
        _require(all(source.closed and source.frame.isNull() and
                   (not isValid(source.timer) or not source.timer.isActive()) for source in sources), 'Native scene acceptance failed')
        result.update(legacy_json=True, versioned_json=True, portable_export_reload=True,
                      web_interaction=True, undo_redo=True, pause_resume=True, resources_released=True)
        return result
    finally:
        if isValid(page):
            page.shutdown_scene()
            page.close()
        release_scene_packages()
        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        QApplication.processEvents()


def main(arguments: list[str] | None = None) -> int:
    """Write explicit success/failure evidence into a new report directory and exit."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-scene-build', nargs=2, required=True, metavar=('FIXTURES', 'REPORT'))
    args = parser.parse_args(arguments)
    fixtures, report = (Path(value).resolve() for value in args.verify_scene_build)
    report.mkdir(parents=True, exist_ok=False)
    previous = Path.cwd()
    result = {'success': False}
    try:
        with tempfile.TemporaryDirectory(prefix='frontengine-acceptance-') as directory:
            os.chdir(directory)
            from PySide6.QtWidgets import QApplication
            from shiboken6 import delete
            application = None
            try:
                application = QApplication([])
                application.setQuitOnLastWindowClosed(False)
                result.update(verify_scene(fixtures, report))
                result['success'] = True
            finally:
                if application is not None:
                    delete(application)
                os.chdir(previous)
    except Exception as error:
        result['error'] = f'{type(error).__name__}: {error}'
    finally:
        os.chdir(previous)
        (report / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return 0 if result['success'] else 1
