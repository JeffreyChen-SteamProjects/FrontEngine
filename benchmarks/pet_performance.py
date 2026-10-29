"""Measure CPU, memory and frame time for one and four desktop pets, legacy sprite vs layered outfit."""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import platform
import statistics
import sys
import tempfile
from pathlib import Path
from time import perf_counter, perf_counter_ns, process_time

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

# Budgets for a 128-pixel pet with its normal repaint timer. The original
# enhancement plan named no figures, so these are stated here and checked below.
BUDGET = {'frame_p95_ms': 4.0, 'cpu_percent_four_pets': 8.0, 'layered_extra_mb_four_pets': 80.0}


def working_set_mb() -> float:
    """Resident memory of this process, without third-party packages."""
    if sys.platform == 'win32':
        class Counters(ctypes.Structure):
            _fields_ = [('cb', ctypes.c_ulong), ('PageFaultCount', ctypes.c_ulong)] + [
                (name, ctypes.c_size_t) for name in (
                    'PeakWorkingSetSize', 'WorkingSetSize', 'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage',
                    'QuotaPeakNonPagedPoolUsage', 'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]
        counters = Counters()
        counters.cb = ctypes.sizeof(Counters)
        kernel = ctypes.windll.kernel32
        kernel.GetCurrentProcess.restype = ctypes.c_void_p
        kernel.K32GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
        if not kernel.K32GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            raise OSError('GetProcessMemoryInfo failed')
        return counters.WorkingSetSize / 2 ** 20
    import resource
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak / 2 ** 20 if sys.platform == 'darwin' else peak / 2 ** 10


def _sprite(folder: Path) -> str:
    image = QImage(128, 128, QImage.Format.Format_ARGB32)
    image.fill(QColor(240, 96, 42))
    path = folder / 'pet.png'
    if not image.save(str(path)):
        raise OSError('Could not write the sprite fixture')
    return str(path)


def _dress(pet, library) -> None:
    from frontengine.show.pet.wardrobe import WardrobeDraft
    draft = WardrobeDraft(pet.profile_session.profiles, pet.profile_session.identifier, library.scan()[0])
    draft.choose_character({'id': 'inkside-mochi', 'version': '1'})
    for piece in ('cafe-beret', 'bow-tie', 'cafe-apron'):
        draft.equip({'id': f'inkside-mochi-{piece}', 'version': '1'})
    draft.apply()


def _wait(app, seconds: float) -> None:
    loop = QEventLoop()
    QTimer.singleShot(int(seconds * 1000), loop.quit)
    loop.exec()


def _frame_times(pets, frames: int) -> list[float]:
    """Time each pet's own per-frame work: composition, mirroring and painting its content.

    QWidget.render would force a GPU framebuffer readback of the overlay compositor,
    which the screen never pays and which is the same for every kind of sprite.
    """
    target = QImage(pets[0].size(), QImage.Format.Format_ARGB32_Premultiplied)
    samples = []
    for index in range(frames):
        pet = pets[index % len(pets)]
        target.fill(0)
        painter = QPainter(target)
        start = perf_counter_ns()
        pet.draw_content(painter)
        samples.append((perf_counter_ns() - start) / 1_000_000)
        painter.end()
        pet._layered_playback._elapsed += 0.033
    return samples


def scenario(app, folder: Path, library, count: int, layered: bool, seconds: float) -> dict:
    from frontengine.show.pet.desktop_pet import DesktopPetWidget
    from frontengine.user_setting.pet_profiles import PetProfiles
    profiles = PetProfiles({}, lambda: None)
    before = working_set_mb()
    pets = [DesktopPetWidget(_sprite(folder), profiles=profiles, talk=False, sit_on_windows=False,
                             asset_library=library) for _ in range(count)]
    try:
        for index, pet in enumerate(pets):
            if layered:
                _dress(pet, library)
            pet.move(80 + index * 160, 200)
            pet.show()
        _wait(app, 1.0)
        # Windows process time ticks every ~16 ms, so the window must be long.
        cpu, wall = process_time(), perf_counter()
        _wait(app, seconds)
        cpu_percent = 100 * (process_time() - cpu) / (perf_counter() - wall)
        samples = _frame_times(pets, 400)
        return {'pets': count, 'layered': layered, 'cpu_percent': round(cpu_percent, 2),
                'working_set_mb': round(working_set_mb(), 1), 'added_mb': round(working_set_mb() - before, 1),
                'frame_median_ms': round(statistics.median(samples), 3),
                'frame_p95_ms': round(sorted(samples)[int(len(samples) * .95)], 3)}
    finally:
        for pet in pets:
            pet.close()
        _wait(app, 0.3)


def _output_path(value: str) -> Path:
    """Results always go to build/; only the file name is taken from the command line."""
    name = os.path.basename(value)
    if not name.endswith('.json'):
        raise SystemExit('--output must name a .json file')
    folder = Path('build')
    folder.mkdir(exist_ok=True)
    return folder / name


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, help='result file name, written under build/')
    parser.add_argument('--seconds', type=float, default=10.0)
    args = parser.parse_args()
    output = _output_path(args.output)
    if not 1 <= args.seconds <= 120:
        parser.error('seconds must be 1..120')
    app = QApplication.instance() or QApplication([])
    from frontengine.show.pet.asset_library import PetAssetLibrary
    from frontengine.show.pet.inkside.library import install_builtin
    with tempfile.TemporaryDirectory(prefix='frontengine-pet-bench-') as temporary:
        folder = Path(temporary)
        library = PetAssetLibrary(folder / 'library')
        install_builtin(library, 'inkside-mochi')
        runs = [scenario(app, folder, library, count, layered, args.seconds)
                for count in (1, 4) for layered in (False, True)]
    four = {run['layered']: run for run in runs if run['pets'] == 4}
    checks = {
        'frame_p95_ms': max(run['frame_p95_ms'] for run in runs) <= BUDGET['frame_p95_ms'],
        'cpu_percent_four_pets': four[True]['cpu_percent'] <= BUDGET['cpu_percent_four_pets'],
        'layered_extra_mb_four_pets':
            four[True]['added_mb'] - four[False]['added_mb'] <= BUDGET['layered_extra_mb_four_pets'],
    }
    result = {'python': sys.version.split()[0], 'os': platform.platform(), 'qt_platform': app.platformName(),
              'screen_dpr': app.primaryScreen().devicePixelRatio(), 'seconds': args.seconds,
              'budget': BUDGET, 'within_budget': checks, 'runs': runs}
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
