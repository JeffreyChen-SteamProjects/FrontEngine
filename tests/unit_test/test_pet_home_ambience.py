"""Ambient sound follows the weather and the hour, stays silent unless chosen and while the home
is not running, keeps its own volume, and releases its players; the strip darkens at night."""
import wave

import pytest
from PySide6.QtCore import QObject
from PySide6.QtGui import QColor, QImage, QPainter

from frontengine.show.pet_game import ambience
from frontengine.show.pet_game.ambience import FOLDER, LOOPS, Ambience, loop_for
from frontengine.show.pet_game.themes import MAX_NIGHT_SHADE, night_shade
from frontengine.utils.pet_game.environment import DAY_MS, sky, weather

HOME = "a" * 32
HOUR = DAY_MS // 24


class FakePlayer(QObject):
    """Records what the ambience asks of a player; never opens an audio device."""

    def __init__(self, made: list, parent=None):
        super().__init__(parent)
        self.source = None
        self.loops = None
        self.volume = None
        self.playing = False
        made.append(self)

    def setSource(self, url):
        self.source = url.toLocalFile()

    def setLoopCount(self, count):
        self.loops = count

    def setVolume(self, volume):
        self.volume = volume

    def play(self):
        self.playing = True

    def stop(self):
        self.playing = False


def _moment(kind):
    """A game time whose loop is ``kind``."""
    for hour in range(24 * 28):
        time_ms = hour * HOUR + HOUR // 2
        if loop_for(HOME, time_ms) == kind:
            return time_ms
    raise AssertionError(kind)


@pytest.fixture
def made():
    return []


@pytest.fixture
def sound(made):
    playing = Ambience(lambda parent: FakePlayer(made, parent))
    playing.set_enabled(True)
    return playing


def test_the_loop_follows_weather_first_then_the_hour():
    for hour in range(24 * 28):
        time_ms = hour * HOUR + HOUR // 2
        current = weather(HOME, time_ms)
        expected = current if current in ("rain", "snow") else ("night" if sky(time_ms) == "night" else "day")
        assert loop_for(HOME, time_ms) == expected
    assert {loop_for(HOME, hour * HOUR) for hour in range(24 * 28)} == set(LOOPS)


def test_every_loop_ships_as_a_short_quiet_wave():
    for name in LOOPS:
        with wave.open(str(FOLDER / f"{name}.wav")) as handle:
            assert (handle.getnchannels(), handle.getsampwidth(), handle.getframerate()) == (1, 2, 22050)
            assert handle.getnframes() == 22050 * 12


def test_it_is_silent_until_chosen_and_while_the_home_is_not_running(made):
    sound = Ambience(lambda parent: FakePlayer(made, parent))
    sound.update(HOME, _moment("day"), running=True)
    assert made == []                                   # off by default: nothing is even loaded
    assert sound.current is None
    sound.set_enabled(True)
    sound.update(HOME, _moment("day"), running=False)
    assert sound.current is None
    sound.update(None, _moment("day"), running=True)    # no home yet
    assert sound.current is None


def test_it_plays_one_looping_track_and_switches_when_the_weather_turns(sound, made):
    sound.update(HOME, _moment("day"), running=True)
    day = made[0]
    assert (sound.current, day.playing, day.loops) == ("day", True, -2)
    assert day.source.endswith("day.wav")
    sound.update(HOME, _moment("rain"), running=True)
    rain = made[1]
    assert (sound.current, day.playing, rain.playing) == ("rain", False, True)
    sound.update(HOME, _moment("day"), running=True)
    assert len(made) == 2                               # players are reused
    assert day.playing
    sound.update(HOME, _moment("day"), running=False)   # paused, locked or in a meeting
    assert not day.playing
    assert sound.current is None


def test_volume_is_its_own_and_zero_means_silence(sound, made):
    sound.set_volume(25)
    sound.update(HOME, _moment("night"), running=True)
    player = made[0]
    assert player.volume == 0.25
    sound.set_volume(80)
    assert player.volume == 0.8
    sound.set_volume(0)
    assert not player.playing
    assert sound.current is None
    sound.set_volume(150)
    assert sound.volume == 100


def test_shutdown_stops_and_releases_every_player(sound, made):
    sound.update(HOME, _moment("day"), running=True)
    sound.update(HOME, _moment("night"), running=True)
    sound.shutdown()
    assert not any(player.playing for player in made)
    assert sound._players == {}
    assert sound.current is None


def test_the_page_setting_turns_it_on_and_remembers_volume(tmp_path, monkeypatch, made):
    from frontengine.show.pet_game.home_service import HomeService
    from frontengine.ui.page.pet_game import home_page
    from frontengine.user_setting.pet_game_save import HomeSaveStore
    from frontengine.user_setting.pet_profiles import PetProfiles
    from frontengine.user_setting.user_setting_file import user_setting_dict
    from frontengine.utils.pet_game.catalog import builtin_catalog

    monkeypatch.setattr(ambience, "_sound_effect", lambda parent: FakePlayer(made, parent))
    monkeypatch.setitem(user_setting_dict, home_page.AMBIENT_KEY, False)
    monkeypatch.setitem(user_setting_dict, home_page.AMBIENT_VOLUME_KEY, 30)
    service = HomeService(None, HomeSaveStore(tmp_path, builtin_catalog()), PetProfiles({}, lambda: None))
    page = home_page.PetHomePage(service)
    try:
        assert not page.ambience.enabled
        assert not page.ambient_slider.isEnabled()
        assert page.ambient_slider.value() == 30
        page.ambient_check.setChecked(True)
        page.ambient_slider.setValue(55)
        assert user_setting_dict[home_page.AMBIENT_KEY] is True
        assert user_setting_dict[home_page.AMBIENT_VOLUME_KEY] == 55
        assert page.ambience.enabled
        assert page.ambience.volume == 55
    finally:
        page.shutdown()
        page.close()


def test_the_strip_tint_is_clear_by_day_deepest_at_midnight_and_spares_clear_pixels():
    assert night_shade(12 * HOUR) == 0
    assert night_shade(0) == MAX_NIGHT_SHADE
    assert 0 < night_shade(19 * HOUR) < MAX_NIGHT_SHADE
    image = QImage(4, 1, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor(0, 0, 0, 0))
    image.setPixelColor(0, 0, QColor(255, 255, 255))
    painter = QPainter(image)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
    painter.fillRect(image.rect(), QColor(28, 34, 78, night_shade(0)))
    painter.end()
    assert image.pixelColor(0, 0).red() < 255                      # a drawn pixel is dimmed
    assert image.pixelColor(1, 0).alpha() == 0                     # a clear one stays click-through
