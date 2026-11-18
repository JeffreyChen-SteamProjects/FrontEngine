"""Pets out on the desktop: when the page lets them go, how the strip hands a roaming pet to its own
window and takes it back, and what the roaming window answers to."""
import pytest
from PySide6.QtCore import QPoint
from PySide6.QtGui import QColor, QImage

from frontengine.show.pet.desktop_pet import SURFACE_FLOOR, SURFACE_LEFT
from frontengine.show.pet_game.home_outing import RETURN_TIMEOUT_MS, outing_action
from frontengine.show.pet_game.home_service import HomeService
from frontengine.ui.page.pet_game import home_page
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.user_setting.user_setting_file import user_setting_dict
from frontengine.utils.pet_game.behaviour import start
from frontengine.utils.pet_game.catalog import builtin_catalog


class _Renderer:
    """A character with a few actions; frames are plain squares."""

    class character:
        canvas = (100, 100)

    actions = {"idle", "walk", "fall", "climb", "sit"}

    def has_action(self, action):
        return action in self.actions

    def render(self, _action, _elapsed, mirrored=False):
        image = QImage(100, 100, QImage.Format.Format_ARGB32)
        image.fill(QColor(200, 80, 40))
        return image


class _Art:
    def renderer(self, _identifier):
        return _Renderer()


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
    for key, value in (("pet_home_running", False), ("pet_home_on_desktop", True), ("pet_home_layer", "top"),
                       ("pet_home_mode", "normal"), (home_page.SCALE_KEY, 100), (home_page.OUTINGS_KEY, True),
                       (home_page.MOTION_KEY, False)):
        monkeypatch.setitem(user_setting_dict, key, value)


@pytest.fixture
def page(tmp_path, *, home_store_factory, lifetime_factory):
    lifetime_factory()
    service = HomeService(None, home_store_factory(tmp_path, builtin_catalog()), PetProfiles({}, lambda: None))
    widget = home_page.PetHomePage(service, lifetime=lifetime_factory())
    widget.create_home()                       # a home with no pets brings a first one
    strip = widget.strip_list[0]
    strip.art = _Art()
    strip.outing_platforms = lambda exclude_hwnds=(): []
    strip.show()
    widget.apply_outings()
    yield widget
    widget.shutdown()
    widget.deleteLater()


def _pet(page):
    return next(iter(page.service.world.residents.values()))


def _send_out(page):
    """Start an outing directly in the world and let one step turn it into time out."""
    world, pet = page.service.world, _pet(page)
    start(world, pet, "outing", "free_time", duration=120_000)
    pet.activity.phase = "using"
    strip = page.strip_list[0]
    strip.sync_outings()
    return strip, pet


def test_outings_are_allowed_only_while_the_strip_shows_them_in_normal_mode(page):
    world = page.service.world
    assert world.outings_allowed
    page.set_mode("focus")
    assert not world.outings_allowed
    page.set_mode("normal")
    assert world.outings_allowed
    page.motion_check.setChecked(True)                      # reduced motion: nobody runs about
    assert not world.outings_allowed
    page.motion_check.setChecked(False)
    page.outings_check.setChecked(False)
    assert not world.outings_allowed and user_setting_dict[home_page.OUTINGS_KEY] is False


def test_turning_outings_off_brings_a_roaming_pet_home(page):
    strip, pet = _send_out(page)
    assert strip.is_out(pet.identifier)
    page.outings_check.setChecked(False)
    assert pet.activity is None or pet.activity.kind != "outing"
    assert strip.outings[pet.identifier].returning_since is not None     # walking back, not vanishing


def test_a_roaming_pet_leaves_the_strip_for_a_window_of_its_own(page):
    strip, pet = _send_out(page)
    roamer = strip.outings[pet.identifier]
    assert roamer.isVisible()
    assert roamer.size().height() == 128                    # the pet's own size on the strip
    box = strip.resident_box(pet)
    assert strip._resident_at(box.center()) is None         # the strip no longer answers for it
    assert not strip.interactive_region().contains(box.center().toPoint())
    area = strip.screen_for_zone().availableGeometry()
    for _ in range(200):
        roamer.step()
        geometry = roamer.geometry()
        assert area.left() <= geometry.left() and geometry.right() <= area.right() + 1
        assert area.top() <= geometry.top() and geometry.bottom() <= area.bottom() + 1


def test_a_finished_outing_walks_back_and_the_strip_draws_the_pet_again(page):
    strip, pet = _send_out(page)
    roamer = strip.outings[pet.identifier]
    for _ in range(30):
        roamer.step()
    assert page.service.run(lambda world: world.call_home(pet.identifier)) == "accepted"
    strip.sync_outings()
    assert roamer.returning_since is not None
    for _ in range(2000):
        if not strip.is_out(pet.identifier):
            break
        roamer.step()
    assert not strip.is_out(pet.identifier)
    box = strip.resident_box(pet)
    assert strip._resident_at(box.center()) == pet.identifier


def test_a_pet_that_cannot_get_back_goes_home_after_a_while(page):
    strip, pet = _send_out(page)
    roamer = strip.outings[pet.identifier]
    now = [100.0]
    roamer._clock = lambda: now[0]
    roamer.home_x = lambda: -10_000                          # somewhere it can never walk to
    roamer.go_home()
    now[0] += RETURN_TIMEOUT_MS / 1000 + 0.1
    roamer.step()
    assert not strip.is_out(pet.identifier)


def test_its_menu_starts_with_come_home(page):
    strip, pet = _send_out(page)
    roamer = strip.outings[pet.identifier]
    menu = roamer.menu(roamer.mapToGlobal(QPoint(5, 5)))
    first = menu.actions()[0]
    assert first.text() == "Come home"
    first.trigger()
    assert pet.activity is None or pet.activity.kind != "outing"
    assert any(action.text() == "Pat" for action in menu.actions())    # then the strip's own menu
    menu.close()


def test_hiding_the_strip_takes_the_roaming_pets_with_it(page):
    strip, pet = _send_out(page)
    roamer = strip.outings[pet.identifier]
    strip.hide()
    assert not strip.outings and not roamer.isVisible()


def test_the_character_shows_what_the_motion_is_doing():
    class Motion:
        _airborne = False
        surface = SURFACE_FLOOR
        state = "walk"

    renderer, motion = _Renderer(), Motion()
    assert outing_action(motion, renderer) == "walk"
    motion.state = "sit"
    assert outing_action(motion, renderer) == "sit"
    motion.state = "groom"                                   # a pose this character lacks
    assert outing_action(motion, renderer) == "idle"
    motion.surface = SURFACE_LEFT
    assert outing_action(motion, renderer) == "climb"
    motion._airborne = True
    assert outing_action(motion, renderer) == "fall"
    assert outing_action(motion, renderer, dragging=True) == "fall"   # no drag pose: falling will do
