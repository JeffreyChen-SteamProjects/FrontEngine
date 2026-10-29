"""Mixed-DPI correctness: physical window edges map per monitor, and pets behave across 100%/125% screens."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from frontengine.show.pet.desktop_pet import native_edges_to_logical

REPO = Path(__file__).resolve().parents[2]


class Point:
    def __init__(self, x, y):
        self._x, self._y = x, y

    def x(self):
        return self._x

    def y(self):
        return self._y


class Screen:
    def __init__(self, name, x, y, width, height, ratio):
        self._name, self._ratio = name, ratio
        self._geometry = (x, y, width, height)

    def name(self):
        return self._name

    def devicePixelRatio(self):
        return self._ratio

    def geometry(self):
        x, y, width, height = self._geometry
        return type('Geometry', (), {'topLeft': lambda _self: Point(x, y), 'width': lambda _self: width,
                                     'height': lambda _self: height})()


def test_physical_edges_become_logical_per_monitor():
    # Qt names screens by monitor model on Windows, so pairing uses origin, then native size.
    screens = [Screen('BenQ A', 0, 0, 1920, 1080, 1.0), Screen('BenQ B', 1920, -164, 1536, 864, 1.25),
               Screen('Shifted', -1100, -200, 1280, 720, 1.5)]
    edges = [(100, 900, 300, 'DISPLAY1', 0, 0, 1920, 1080),
             (2420, 3420, 336, 'DISPLAY6', 1920, -164, 1920, 1080),
             (-1900, -1000, 100, 'DISPLAY3', -1920, -300, 1920, 1080),
             (7, 70, 9, 'missing', 5000, 5000, 640, 480)]
    assert native_edges_to_logical(edges, screens) == [
        (100, 900, 300), (2320, 3120, 236), (-1087, -487, 67), (7, 70, 9)]


@pytest.mark.skipif(sys.platform != 'win32', reason='Win32 monitor information')
def test_windows_reports_each_window_with_its_monitor():
    from frontengine.utils.platform_info.platform_info import standable_windows_native
    for left, right, top, device, monitor_left, monitor_top, width, height in standable_windows_native():
        assert right > left and isinstance(device, str) and isinstance(monitor_left, int)
        assert isinstance(top, int) and isinstance(monitor_top, int) and width > 0 and height > 0


def test_pets_across_two_screens_with_different_scaling(tmp_path):
    pytest.importorskip('Imervue.puppet.document_io')
    sys.path.insert(0, str(REPO / 'tests' / 'integration'))
    try:
        from pet_mixed_dpi import LAYOUT
    finally:
        sys.path.pop(0)
    (tmp_path / 'screens.json').write_text(json.dumps(LAYOUT), encoding='utf-8')
    environment = {**os.environ, 'QT_QPA_PLATFORM': 'offscreen:configfile=screens.json',
                   'PYTHONPATH': os.pathsep.join((str(REPO), str(REPO / 'tests' / 'integration')))}
    completed = subprocess.run([sys.executable, str(REPO / 'tests' / 'integration' / 'pet_mixed_dpi.py')],
                               cwd=tmp_path, env=environment, capture_output=True, text=True, timeout=300,
                               check=False, shell=False)
    result = json.loads(completed.stdout.strip().splitlines()[-1])
    assert result['status'] == 'passed', result.get('traceback')
    assert result['perched_logical_feet'] == 400
    assert set(result['puppet_arrivals']) == {'DISPLAY1', 'DISPLAY2'}
