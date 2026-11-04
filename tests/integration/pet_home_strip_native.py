"""Native check of the desktop home strip on an isolated Windows desktop.

Usage (Windows, from the repository root)::

    py tests/integration/pet_home_strip_native.py OUTPUT_DIR

Builds a home in a temporary working directory, puts an ordinary window behind
the strip, and asks Win32 which window owns given screen points: empty strip
pixels must belong to the window behind (click-through), residents, furniture
and the home button to the strip. Also checks that showing the strip does not
change the foreground window and that the layer choice toggles WS_EX_TOPMOST, and that
while it rains the weather layer is shown over the strip without changing any of that.
Writes OUTPUT_DIR/result.json and a screenshot. Never touches the user's desktop.
"""
import ctypes
import json
import os
import sys
import tempfile
import traceback
from ctypes import wintypes
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))  # test this checkout, never an installed frontengine
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hidden_desktop import is_child, run_on_hidden_desktop  # noqa: E402

OUTPUT = Path(sys.argv[1]).resolve()
OUTPUT.mkdir(parents=True, exist_ok=True)
if not is_child(OUTPUT):
    raise SystemExit(run_on_hidden_desktop(__file__, str(OUTPUT)))

os.chdir(tempfile.mkdtemp(prefix='fe-home-strip-'))
from PySide6.QtCore import QEventLoop, QPoint, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

app = QApplication(sys.argv)
user32 = ctypes.WinDLL('user32', use_last_error=True)
user32.WindowFromPoint.argtypes = [wintypes.POINT]
user32.WindowFromPoint.restype = wintypes.HWND
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = ctypes.c_long
GA_ROOT, GWL_EXSTYLE, WS_EX_TOPMOST = 2, -20, 0x8


def wait(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop, loop.quit)
    loop.exec()


def owner(widget: QWidget, local: QPoint) -> int:
    """Root window under a strip-local logical point, asked in physical pixels."""
    screen = widget.screen()
    if screen.geometry().topLeft() != QPoint(0, 0):
        raise RuntimeError('This hit-test probe requires the primary monitor at native origin')
    logical = widget.mapToGlobal(local) - screen.geometry().topLeft()
    ratio = screen.devicePixelRatio()
    physical = wintypes.POINT(int(logical.x() * ratio), int(logical.y() * ratio))
    hwnd = user32.WindowFromPoint(physical)
    return int(user32.GetAncestor(hwnd, GA_ROOT) or 0)


def topmost(widget: QWidget) -> bool:
    return bool(user32.GetWindowLongW(int(widget.winId()), GWL_EXSTYLE) & WS_EX_TOPMOST)


def rain(strip, world, points, behind_hwnd) -> dict:
    """Make it rain: the weather layer shows over the strip and every click still lands as before."""
    from frontengine.show.pet_game.strip_weather import precipitation
    foreground = int(user32.GetForegroundWindow() or 0)
    hour = world.time_ms
    while precipitation(world.home, hour) != 'rain':
        hour += 60_000 * 15
    world.time_ms = hour
    strip._stepped()
    wait(600)
    layer = strip.weather_layer
    layer.grab().save(str(OUTPUT / 'rain-layer.png'))
    resident = next(iter(world.residents.values()))
    points = dict(points, resident=strip.resident_center(resident).toPoint())
    owners = {name: owner(strip, point) for name, point in points.items()}
    strip_hwnd = int(strip.winId())
    return {'rain_shown': layer.isVisible() and layer.geometry() == strip.geometry(),
            'rain_layer_hwnd': int(layer.winId()), 'rain_owners': owners,
            'rain_empty_passes_through': owners['empty'] == behind_hwnd,
            'rain_items_take_input': all(owners[name] == strip_hwnd for name in ('furniture', 'resident', 'button')),
            'rain_foreground_unchanged': int(user32.GetForegroundWindow() or 0) == foreground}


def larger(page, strip, behind_hwnd) -> dict:
    """At 200 % the home is wider than the screen: it stays on its screen, scrolls to the pet,
    and the pet still takes clicks while the empty strip still passes them through."""
    world = strip.service.world
    pet = next(iter(world.residents.values()))
    strip.service.pause('native-geometry-probe')
    previous_x = pet.x_milli
    pet.x_milli = (world.zones[strip.zone].width_pixels - 40) * 1000
    strip._before = strip._after = {}
    page.set_strip_scale(200)
    strip.chosen = pet.identifier
    strip._stepped()
    wait(1500)
    area = strip.screen_for_zone().availableGeometry()
    box = strip.resident_box(pet)
    empty = next((QPoint(x, strip.height() - 30) for x in range(strip.width() - 12, 0, -20)
                  if not strip.interactive_region().contains(QPoint(x, strip.height() - 30))), None)
    if empty is None:
        raise RuntimeError('No empty point available for the enlarged strip hit test')
    result = {'large_size': [strip.width(), strip.height()], 'large_scroll': strip.scroll_x,
              'large_on_screen': area.contains(strip.geometry()),
              'large_pet_takes_input': owner(strip, box.center().toPoint()) == int(strip.winId()),
              'large_scrolled': strip.scroll_x > 0,
              'large_empty_passes_through': owner(strip, empty) == behind_hwnd}
    strip.grab().save(str(OUTPUT / 'strip-200.png'))
    pet.x_milli = previous_x
    strip._before = strip._after = {}
    strip.service.resume('native-geometry-probe')
    page.set_strip_scale(100)
    wait(400)
    return result


def run() -> dict:
    from frontengine.show.pet_game.home_service import HomeService
    from frontengine.ui.page.pet_game.home_page import PetHomePage
    from frontengine.user_setting.pet_game_save import HomeSaveStore
    from frontengine.user_setting.pet_profiles import PetProfiles
    from frontengine.user_setting.user_setting_file import user_setting_dict
    from frontengine.utils.pet_game.catalog import builtin_catalog

    user_setting_dict.update(pet_home_on_desktop=True, pet_home_layer='top')
    behind = QWidget()
    behind.setWindowTitle('behind the strip')
    area = app.primaryScreen().availableGeometry()
    behind.setGeometry(area.left(), area.bottom() - 400, area.width(), 400)
    behind.show()
    behind.activateWindow()
    wait(400)
    behind.setGeometry(area.left(), area.bottom() - 400, area.width(), 400)
    wait(200)
    foreground_before = int(user32.GetForegroundWindow() or 0)
    service = HomeService(None, HomeSaveStore(Path.cwd(), builtin_catalog()), PetProfiles({}, lambda: None))
    page = PetHomePage(service)
    page.create_home()
    page.residents.new_pet()          # creating a home already sets out the bed, table and desk
    wait(1200)
    strip = page.strip_list[0]
    strip.grab().save(str(OUTPUT / 'strip.png'))
    world = service.world
    piece, definition = world.in_zone(page.zone)[0]
    resident = next(iter(world.residents.values()))
    points = {
        'empty': QPoint(strip.width() - 12, strip.height() - 30),
        'furniture': strip.piece_rect(piece, definition).center().toPoint(),
        'resident': strip.resident_center(resident).toPoint(),
        'button': strip.button.geometry().center(),
    }
    if not behind.geometry().contains(strip.mapToGlobal(points['empty'])):
        raise RuntimeError('The backing window does not cover the empty test point')
    owners = {name: owner(strip, point) for name, point in points.items()}
    strip_hwnd, behind_hwnd = int(strip.winId()), int(behind.winId())
    result = {
        'strip_geometry': strip.geometry().getRect(),
        'behind_geometry': behind.geometry().getRect(),
        'screen_geometry': strip.screen().geometry().getRect(),
        'screen_ratio': strip.screen().devicePixelRatio(),
        'empty_global': strip.mapToGlobal(points['empty']).toTuple(),
        'strip_hwnd': strip_hwnd, 'behind_hwnd': behind_hwnd, 'owners': owners,
        'empty_passes_through': owners['empty'] == behind_hwnd,
        'items_take_input': all(owners[name] == strip_hwnd for name in ('furniture', 'resident', 'button')),
        'foreground_unchanged': int(user32.GetForegroundWindow() or 0) == foreground_before,
        'topmost_when_top': topmost(strip),
    }
    result.update(rain(strip, world, points, behind_hwnd))
    result.update(larger(page, strip, behind_hwnd))
    page.choose_layer('bottom')
    wait(400)
    result['topmost_when_bottom'] = topmost(strip)
    result['bottom_hwnd'] = int(strip.winId())          # changing flags may recreate the native window
    result['bottom_empty_passes_through'] = owner(strip, points['empty']) == behind_hwnd
    page.choose_layer('top')
    wait(400)
    page.layout_panel.toggle_arrange()
    wait(200)
    result['arranging_takes_empty'] = owner(strip, points['empty']) == int(strip.winId())
    page.layout_panel.toggle_arrange()
    wait(200)
    result['after_arranging_passes_through'] = owner(strip, points['empty']) == behind_hwnd
    result['shutdown'] = page.shutdown()
    result['passed'] = (result['empty_passes_through'] and result['items_take_input']
                        and result['foreground_unchanged'] and result['topmost_when_top']
                        and not result['topmost_when_bottom'] and result['arranging_takes_empty']
                        and result['after_arranging_passes_through'] and result['rain_shown']
                        and result['rain_empty_passes_through'] and result['rain_items_take_input']
                        and result['rain_foreground_unchanged'] and result['large_on_screen']
                        and result['large_pet_takes_input'] and result['large_empty_passes_through']
                        and result['large_scrolled'] and result['bottom_empty_passes_through']
                        and result['shutdown'])
    return result


try:
    report = run()
except Exception:
    report = {'passed': False, 'error': traceback.format_exc()}
(OUTPUT / 'result.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
sys.exit(0 if report.get('passed') else 1)
