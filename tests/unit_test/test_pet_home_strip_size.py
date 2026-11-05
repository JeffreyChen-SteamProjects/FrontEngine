"""The desktop strip at a chosen size: everything scales, a home larger than its screen scrolls to keep
the pet in view, Ctrl+wheel and the ⌂ menu change the size, the page remembers it, and a
double-click pats a pet."""
import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent, QWheelEvent

from frontengine.show.pet_game.home_service import HomeService
from frontengine.show.pet_game.home_strip import SCALES, STRIP_HEIGHT
from frontengine.ui.page.pet_game import home_page
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.user_setting.user_setting_file import user_setting_dict
from frontengine.utils.pet_game.catalog import CELL_PIXELS, builtin_catalog


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
    for key, value in (("pet_home_running", False), ("pet_home_on_desktop", True), ("pet_home_layer", "top"),
                       ("pet_home_mode", "normal"), (home_page.SCALE_KEY, 100)):
        monkeypatch.setitem(user_setting_dict, key, value)


@pytest.fixture
def page(tmp_path, *, home_store_factory, lifetime_factory):
    lifetime_factory()
    service = HomeService(None, home_store_factory(tmp_path, builtin_catalog()), PetProfiles({}, lambda: None))
    widget = home_page.PetHomePage(service, lifetime=lifetime_factory())
    widget.create_home()
    # creating a home with no pets brings a first one
    yield widget
    widget.shutdown()
    widget.deleteLater()


def _strip(page):
    assert len(page.strip_list) == 1
    return page.strip_list[0]


def _pet(strip):
    return next(iter(strip.service.world.residents.values()))


def _wheel(strip, up: bool, ctrl: bool) -> QWheelEvent:
    return QWheelEvent(QPointF(10, 10), QPointF(10, 10), QPoint(), QPoint(0, 120 if up else -120),
                       Qt.MouseButton.NoButton,
                       Qt.KeyboardModifier.ControlModifier if ctrl else Qt.KeyboardModifier.NoModifier,
                       Qt.ScrollPhase.NoScrollPhase, False)


def test_everything_scales_with_the_size(page):
    strip = _strip(page)
    piece, definition = strip.service.world.in_zone(strip.zone)[0]
    normal = strip.piece_rect(piece, definition)
    assert (strip.cell_width(), strip.height()) == (CELL_PIXELS, STRIP_HEIGHT)
    page.set_strip_scale(150)
    assert strip.cell_width() == CELL_PIXELS * 1.5
    assert strip.height() == STRIP_HEIGHT * 1.5
    assert strip.piece_rect(piece, definition).width() == normal.width() * 1.5
    assert strip.width() <= strip.screen_for_zone().availableGeometry().width()     # never past its screen
    page.set_strip_scale(75)
    assert strip.height() == round(STRIP_HEIGHT * 0.75)
    assert strip.max_scroll() == 0


def test_a_home_larger_than_its_screen_scrolls_to_keep_the_chosen_pet_in_view(page):
    strip = _strip(page)
    page.set_strip_scale(200)
    assert strip.max_scroll() > 0
    pet = _pet(strip)
    pet.x_milli = (strip.service.world.zones[strip.zone].width_pixels - 40) * 1000      # far right
    strip._before = strip._after = {}
    strip.chosen = pet.identifier
    strip._stepped()
    for _ in range(60):
        strip._ease_scroll()
    box = strip.resident_box(pet)
    assert strip.scroll_x > 0
    assert 0 <= box.center().x() <= strip.width()
    assert strip._resident_at(box.center()) == pet.identifier                   # hit-testing follows the scroll
    assert strip.interactive_region().contains(box.center().toPoint())          # and so does the input mask
    cell = 7
    assert strip.x_cell(strip.cell_x(cell)) == pytest.approx(cell)


def test_ctrl_wheel_asks_for_the_next_size_and_a_plain_wheel_does_nothing(page):
    strip = _strip(page)
    asked = []
    strip.scale_requested.connect(asked.append)
    strip.wheelEvent(_wheel(strip, up=True, ctrl=False))
    assert asked == []
    strip.wheelEvent(_wheel(strip, up=True, ctrl=True))
    strip.wheelEvent(_wheel(strip, up=False, ctrl=True))
    assert asked == [125, 100]                                           # the page applied 125 in between
    page.set_strip_scale(SCALES[-1])
    strip.wheelEvent(_wheel(strip, up=True, ctrl=True))                    # already the largest
    assert asked == [125, 100]                                           # the page applied 125 in between


def test_the_page_remembers_the_size_and_new_strips_use_it(page):
    page.set_strip_scale(125)
    assert user_setting_dict[home_page.SCALE_KEY] == 125
    assert page.scale_combo.currentData() == 125
    page.desktop_check.setChecked(False)
    page.desktop_check.setChecked(True)
    assert round(_strip(page).scale * 100) == 125
    page.set_strip_scale(130)                                                 # not a size: ignored
    assert user_setting_dict[home_page.SCALE_KEY] == 125


def test_the_home_menu_offers_every_size_with_the_current_one_checked(page):
    strip = _strip(page)
    strip._fill_home_menu()
    sizes = next(action.menu() for action in strip.button.menu().actions()
                 if action.menu() is not None and [a.text() for a in action.menu().actions()] == [f"{p}%" for p in SCALES])
    assert [a.isChecked() for a in sizes.actions()] == [p == 100 for p in SCALES]
    asked = []
    strip.scale_requested.connect(asked.append)
    sizes.actions()[-1].trigger()
    assert asked == [200]


def test_double_clicking_a_pet_pats_it(page):
    strip = _strip(page)
    pet = _pet(strip)
    mood, affection = pet.needs["mood"], pet.affection
    center = strip.resident_box(pet).center()
    event = QMouseEvent(QMouseEvent.Type.MouseButtonDblClick, center, strip.mapToGlobal(center.toPoint()).toPointF(),
                        Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    strip.mouseDoubleClickEvent(event)
    assert pet.needs["mood"] == min(100, mood + 8)
    assert pet.affection == affection + 1


@pytest.mark.parametrize("edge", ["left", "right"])
def test_edge_caption_remains_inside_strip_and_its_input_mask(page, edge):
    strip = _strip(page)
    pet = _pet(strip)
    pet.x_milli = 0 if edge == "left" else strip.service.world.zones[strip.zone].width_pixels * 1000
    strip._before = strip._after = {}
    strip.chosen = pet.identifier
    strip._stepped()
    for _ in range(60):
        strip._ease_scroll()
    caption = strip.caption_rect(pet)
    assert caption.left() >= 0 and caption.right() <= strip.width()
    assert strip.interactive_region().contains(caption.toAlignedRect())
