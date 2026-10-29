"""Source and frozen-executable acceptance with isolated settings and durable evidence."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import traceback


def executable_image():
    """Locate the running image independently of a frozen runtime's sys.executable."""
    if sys.platform == 'win32':
        import ctypes
        path = ctypes.create_unicode_buffer(32768)
        get_path = ctypes.WinDLL('kernel32', use_last_error=True).GetModuleFileNameW
        get_path.argtypes = (ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32)
        get_path.restype = ctypes.c_uint32
        length = get_path(None, path, len(path))
        if not length or length >= len(path):
            raise ctypes.WinError(ctypes.get_last_error())
        return Path(path.value).resolve(strict=True)
    if sys.platform == 'linux':
        return Path('/proc/self/exe').resolve(strict=True)
    return Path(sys.argv[0]).resolve(strict=True)


@contextmanager
def isolated_directory(path):
    original = Path.cwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(original)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-3d-scene-build', '--report', dest='report', type=Path)
    parser.add_argument('--require-compiled', action='store_true')
    parser.add_argument('--camera', action='store_true', help='Require real OBS virtual camera send and receive')
    parser.add_argument('--stress-vertices', type=int, default=0)
    parser.add_argument('--media-fixtures', type=Path)
    args = parser.parse_args(argv)
    if args.stress_vertices and not 10000 <= args.stress_vertices <= 1000000:
        parser.error('Stress vertices must be within 10000–1000000')
    report = args.report.resolve() if args.report else None
    media_fixtures = args.media_fixtures.resolve() if args.media_fixtures else None
    if report is not None:
        report.mkdir(parents=True, exist_ok=False)
    result = {'completed': False, 'timestamp_utc': datetime.now(timezone.utc).isoformat(),
              'compiled': '__compiled__' in globals(), 'camera': 'not_run', 'stress': 'not_run', 'media': 'not_run'}
    original = Path.cwd()
    try:
        if args.require_compiled and not result['compiled']:
            raise RuntimeError('This acceptance gate requires the compiled executable')
        executable = executable_image() if result['compiled'] else None
        os.environ.pop('QT_QPA_PLATFORM', None)
        with tempfile.TemporaryDirectory(prefix='frontengine-3d-acceptance-') as temporary, isolated_directory(temporary):
            from PySide6.QtGui import QSurfaceFormat
            from PySide6.QtWidgets import QApplication
            from frontengine.show.scene.view3d import surface_format
            if QApplication.instance() is None:
                QSurfaceFormat.setDefaultFormat(surface_format())
            from frontengine.utils.scene_format.scene_3d_verification import verify_native_scene
            result.update(verify_native_scene())
            from PySide6 import __version__ as qt_version
            result['pyside6_version'] = qt_version
            if media_fixtures:
                from frontengine.utils.scene_format.scene_3d_media_acceptance import verify_media
                result['media'] = verify_media(media_fixtures)
            if args.camera:
                from frontengine.utils.scene_format.scene_3d_camera_acceptance import verify_camera
                result['camera'] = verify_camera()
            if args.stress_vertices:
                from frontengine.utils.scene_format.scene_3d_stress import verify_stress
                result['stress'] = verify_stress(Path(temporary), args.stress_vertices)
            if result['compiled']:
                digest = hashlib.sha256()
                with executable.open('rb') as stream:
                    for block in iter(lambda: stream.read(1024*1024), b''):
                        digest.update(block)
                result['executable_sha256'] = digest.hexdigest()
                result['executable_path'] = str(executable)
            result['completed'] = True
    except Exception as error:
        result['error'] = str(error)
        result['traceback'] = traceback.format_exc()
    finally:
        os.chdir(original)
        if report is not None:
            (report/'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0 if result['completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
