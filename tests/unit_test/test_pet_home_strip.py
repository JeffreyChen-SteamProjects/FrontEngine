"""The home on the desktop: input only where something is, hiding pauses, smooth drawing."""
import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent

from frontengine.show.pet_game.home_service import HomeService
from frontengine.show.pet_game.home_strip import FRAME_MS, HIDDEN_REASON, HomeStrip
from frontengine.ui.page.pet_game.home_page import PetHomePage
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.pet_game.catalog import builtin_catalog


class Clock:
    def __init__(self) -> None:
        self.now = 10.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
    from frontengine.user_setting.user_setting_file import user_setting_dict
    for key, value in (("pet_home_running", False), ("pet_home_on_desktop", True), ("pet_home_layer", "top"),
                       ("pet_home_mode", "normal")):
        monkeypatch.setitem(user_setting_dict, key, value)


@pytest.fixture
def page(tmp_path, *, home_store_factory, lifetime_factory):
    lifetime_factory()
    clock = Clock()
    service = HomeService(None, home_store_factory(tmp_path, builtin_catalog()), PetProfiles({}, lambda: None),
                          clock=clock)
    widget = PetHomePage(service, lifetime=lifetime_factory())
    widget.clock = clock
    widget.create_home()                      # the starter kit is set out by itself
    # creating a home with no pets brings a first one
    yield widget
    widget.shutdown()
    widget.deleteLater()


def _strip(page) -> HomeStrip:
    assert len(page.strip_list) == 1
    return page.strip_list[0]


def _mouse(kind, point, button=Qt.MouseButton.LeftButton):
    point = QPointF(point)
    return QMouseEvent(kind, point, point, button, button, Qt.KeyboardModifier.NoModifier)


def test_a_new_home_appears_on_the_desktop_above_windows_without_focus(page):
    strip = _strip(page)
    assert strip.isVisible()
    flags = strip.windowFlags()
    assert flags & Qt.WindowType.WindowStaysOnTopHint
    assert flags & Qt.WindowType.WindowDoesNotAcceptFocus
    assert strip.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    page.choose_layer("bottom")
    assert strip.windowFlags() & Qt.WindowType.WindowStaysOnBottomHint
    assert not strip.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    assert strip.isVisible()


def test_only_residents_furniture_and_the_button_take_the_mouse(page):
    strip = _strip(page)
    world = page.service.world
    region = strip.mask()
    for piece, definition in world.in_zone(page.zone):
        assert region.contains(strip.piece_rect(piece, definition).center().toPoint())
    resident = next(iter(world.residents.values()))
    assert region.contains(strip.resident_center(resident).toPoint())
    assert region.contains(strip.button.geometry().center())
    empty = QPoint(strip.width() - 10, strip.height() - 8)
    assert not region.contains(empty)
    page.layout_panel.toggle_arrange()
    assert strip.mask().contains(empty)
    page.layout_panel.toggle_arrange()
    assert not strip.mask().contains(empty)


def test_hiding_the_home_pauses_it_and_closing_does_not(page):
    page.service.start()
    strip = _strip(page)
    strip.hide()
    assert HIDDEN_REASON in page.service.pause_reasons
    assert not page.service.running
    strip.show()
    assert page.service.running
    strip.close()
    assert page.service.running
    assert not page.strip_list
    page.desktop_check.setChecked(False)
    page.desktop_check.setChecked(True)
    assert len(page.strip_list) == 1


def test_drawing_interpolates_between_world_steps(page):
    page.service.start()
    clock = page.clock
    strip = _strip(page)
    strip._clock = clock
    resident = next(iter(page.service.world.residents.values()))
    resident.x_milli = 10_000
    strip._stepped()
    resident.x_milli = 22_800
    strip._stepped()
    clock.now += 0.1
    assert strip.resident_x_milli(resident) == pytest.approx(16_400)
    clock.now += 0.2
    assert strip.resident_x_milli(resident) == pytest.approx(22_800)


def test_quality_tier_sets_the_frame_rate(page):
    strip = _strip(page)
    for tier, interval in FRAME_MS.items():
        strip.set_quality_tier(tier)
        assert strip.frame_timer.interval() == interval


@pytest.mark.parametrize('interrupt', ['hide', 'close', 'ungrab', 'meeting'])
def test_interrupted_drag_releases_resident(page, interrupt):
    from frontengine.utils.pet_game.simulation import advance

    strip = _strip(page)
    resident = next(iter(page.service.world.residents.values()))
    center = strip.resident_center(resident)
    original_x = resident.x_milli
    strip.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, center))
    strip.mouseMoveEvent(_mouse(QEvent.Type.MouseMove, center + QPointF(200, 0)))
    assert resident.activity.kind == 'drag'
    if interrupt == 'ungrab':
        from PySide6.QtWidgets import QApplication
        QApplication.sendEvent(strip, QEvent(QEvent.Type.UngrabMouse))
    elif interrupt == 'meeting':
        page.set_mode('meeting')
        page.set_mode('normal')
    else:
        getattr(strip, interrupt)()
    assert resident.x_milli == original_x
    advance(page.service.world, 1000)
    assert resident.activity is None or resident.activity.kind != 'drag'
    if interrupt == 'hide':
        strip.show()
        empty = QPoint(strip.width() - 10, strip.height() - 8)
        assert not strip.mask().contains(empty)


def test_other_button_release_does_not_finish_left_drag(page):
    strip = _strip(page)
    resident = next(iter(page.service.world.residents.values()))
    center = strip.resident_center(resident)
    target = center + QPointF(200, 0)
    strip.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, center))
    strip.mouseMoveEvent(_mouse(QEvent.Type.MouseMove, target))
    strip.mouseReleaseEvent(_mouse(QEvent.Type.MouseButtonRelease, target, Qt.MouseButton.RightButton))
    assert resident.activity is not None and resident.activity.kind == 'drag'
    strip.mouseReleaseEvent(_mouse(QEvent.Type.MouseButtonRelease, target))
    assert resident.activity is None or resident.activity.kind != 'drag'


def test_resident_moving_out_during_drag_can_be_released(page):
    strip = _strip(page)
    resident = next(iter(page.service.world.residents.values()))
    center = strip.resident_center(resident)
    strip.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, center))
    strip.mouseMoveEvent(_mouse(QEvent.Type.MouseMove, center + QPointF(200, 0)))
    assert page.service.release(resident.identifier) == 'accepted'
    strip.mouseReleaseEvent(_mouse(QEvent.Type.MouseButtonRelease, center))
    assert resident.identifier not in page.service.world.residents
    assert not strip.mask().contains(QPoint(strip.width() - 10, strip.height() - 8))


def test_late_drag_release_preserves_new_command(page):
    strip = _strip(page)
    resident = next(iter(page.service.world.residents.values()))
    original_x = resident.x_milli
    center = strip.resident_center(resident)
    target = center + QPointF(200, 0)
    strip.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, center))
    strip.mouseMoveEvent(_mouse(QEvent.Type.MouseMove, target))
    assert page.service.run(lambda world: world.command(resident.identifier, 'sleep')) == 'accepted'
    strip.mouseReleaseEvent(_mouse(QEvent.Type.MouseButtonRelease, target))
    assert resident.x_milli == original_x
    assert resident.commands == ['sleep']


def test_right_click_commands_and_drag(page):
    strip = _strip(page)
    world = page.service.world
    resident = next(iter(world.residents.values()))
    center = strip.resident_center(resident)
    strip.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, center, Qt.MouseButton.RightButton))
    ask = next(action.menu() for action in strip.last_menu.actions() if action.text() == "Ask to")
    sleep = next(action for action in ask.actions() if action.text() == "Sleep")
    sleep.trigger()
    assert resident.commands == ["sleep"]
    strip.last_menu.close()
    strip.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, center))
    target = QPointF(center.x() + 200, center.y())
    strip.mouseMoveEvent(_mouse(QEvent.Type.MouseMove, target))
    assert resident.activity.kind == "drag"
    strip.mouseReleaseEvent(_mouse(QEvent.Type.MouseButtonRelease, target))
    assert resident.activity is None
    assert resident.x_milli == pytest.approx(target.x() * 1000, abs=1000)


def test_clicking_a_resident_selects_it_in_the_page(page):
    strip = _strip(page)
    resident = next(iter(page.service.world.residents.values()))
    page.select_resident(None)
    center = strip.resident_center(resident)
    strip.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, center))
    strip.mouseReleaseEvent(_mouse(QEvent.Type.MouseButtonRelease, center))
    assert page.selected_resident == resident.identifier
