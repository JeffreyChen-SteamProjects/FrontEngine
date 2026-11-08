"""Rain and snow over the desktop strip: a layer of its own that never takes input, shown only
while it rains or snows on a shown, non-quiet strip, and gone with the strip."""
import pytest
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter

from frontengine.show.pet_game.home_service import HomeService
from frontengine.show.pet_game.strip_weather import paint_precipitation, precipitation
from frontengine.ui.page.pet_game.home_page import PetHomePage
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.environment import DAY_MS, weather

HOUR = DAY_MS // 24


def _moment(home, kinds):
    for hour in range(24 * 28):
        time_ms = hour * HOUR + HOUR // 2
        if weather(home, time_ms) in kinds:
            return time_ms
    raise AssertionError(kinds)


def _drawn(kind, elapsed, moving=True) -> QImage:
    image = QImage(400, 150, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    paint_precipitation(painter, QRectF(image.rect()), kind, elapsed, moving)
    painter.end()
    return image


def _painted(image: QImage) -> int:
    return sum(1 for x in range(0, image.width(), 2) for y in range(0, image.height(), 2)
               if image.pixelColor(x, y).alpha())


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
    from frontengine.user_setting.user_setting_file import user_setting_dict
    for key, value in (("pet_home_running", False), ("pet_home_on_desktop", True), ("pet_home_layer", "top"),
                       ("pet_home_mode", "normal")):
        monkeypatch.setitem(user_setting_dict, key, value)


@pytest.fixture
def strip(tmp_path, *, home_store_factory, lifetime_factory):
    lifetime_factory()
    service = HomeService(None, home_store_factory(tmp_path, builtin_catalog()), PetProfiles({}, lambda: None))
    page = PetHomePage(service, lifetime=lifetime_factory())
    page.create_home()
    assert len(page.strip_list) == 1
    yield page.strip_list[0]
    page.shutdown()
    page.deleteLater()


def _weather_at(strip, kinds):
    world = strip.service.world
    world.time_ms = _moment(world.home, kinds)
    strip._stepped()


def test_only_rain_and_snow_fall():
    home = "a" * 32
    assert precipitation(home, _moment(home, ("rain",))) == "rain"
    assert precipitation(home, _moment(home, ("snow",))) == "snow"
    assert precipitation(home, _moment(home, ("clear",))) is None
    assert precipitation(home, _moment(home, ("cloudy",))) is None


@pytest.mark.parametrize("kind", ["rain", "snow"])
def test_drops_cover_little_of_the_strip_move_with_time_and_stand_still_under_reduced_motion(kind):
    first = _drawn(kind, 0)
    assert 0 < _painted(first) < 400 * 150 // 4 * 0.15           # light weather, the desktop stays readable
    assert first != _drawn(kind, 500)
    assert _drawn(kind, 0, moving=False) == _drawn(kind, 500, moving=False)


def test_the_layer_shows_over_the_strip_only_while_it_rains_and_never_takes_input(strip):
    layer = strip.weather_layer
    _weather_at(strip, ("rain",))
    assert layer.isVisible()
    assert layer.geometry() == strip.geometry()
    assert layer.windowFlags() & Qt.WindowType.WindowTransparentForInput
    assert layer.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus
    assert layer.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    _weather_at(strip, ("clear", "cloudy"))
    assert not layer.isVisible()
    _weather_at(strip, ("snow",))
    assert layer.isVisible()
    assert layer.kind == "snow"


def test_the_layer_follows_hiding_quiet_modes_layer_and_closing(strip):
    layer = strip.weather_layer
    _weather_at(strip, ("rain",))
    strip.hide()
    assert not layer.isVisible()
    strip.show()
    assert layer.isVisible()
    strip.quiet = True                     # focus and meeting modes
    strip._stepped()
    assert not layer.isVisible()
    strip.quiet = False
    strip.set_layer("bottom")
    strip._stepped()
    assert layer.windowFlags() & Qt.WindowType.WindowStaysOnBottomHint
    assert layer.isVisible()
    strip.move(strip.x() + 10, strip.y())
    assert layer.geometry() == strip.geometry()
    destroyed = []
    layer.destroyed.connect(lambda: destroyed.append(True))
    strip.close()
    from PySide6.QtCore import QCoreApplication, QEvent
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert destroyed
