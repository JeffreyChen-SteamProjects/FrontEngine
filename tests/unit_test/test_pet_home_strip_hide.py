"""Hiding the desktop home from its own menu also unticks *Show the home on the desktop*."""
import pytest

from frontengine.show.pet_game.home_service import HomeService
from frontengine.ui.page.pet_game.home_page import DESKTOP_KEY, PetHomePage
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.multi_language.retranslate import translate
from frontengine.utils.pet_game.catalog import builtin_catalog


@pytest.fixture
def page(tmp_path, monkeypatch, *, home_store_factory, lifetime_factory):
    from frontengine.user_setting.user_setting_file import user_setting_dict
    monkeypatch.setitem(user_setting_dict, "pet_home_running", False)
    monkeypatch.setitem(user_setting_dict, DESKTOP_KEY, True)
    lifetime_factory()
    service = HomeService(None, home_store_factory(tmp_path, builtin_catalog()), PetProfiles({}, lambda: None))
    widget = PetHomePage(service, lifetime=lifetime_factory())
    yield widget
    monkeypatch.undo()
    assert widget.shutdown()
    widget.deleteLater()


def _hide_action(strip):
    strip._fill_home_menu()
    return next(action for action in strip.button.menu().actions()
                if action.text() == translate("pet_home_hide", "Hide the home"))


def test_hiding_the_home_from_its_menu_unticks_the_setting(page):
    from frontengine.user_setting.user_setting_file import user_setting_dict
    page.desktop_check.setChecked(True)
    page.create_home()
    assert page.strip_list and page.desktop_check.isChecked()
    _hide_action(page.strip_list[0]).trigger()
    assert not page.desktop_check.isChecked()
    assert user_setting_dict[DESKTOP_KEY] is False
    assert page.strip_list == []
    page.desktop_check.setChecked(True)               # ticking it again brings the home back
    assert page.strip_list and page.strip_list[0].isVisible()


def _mouse(kind, x, y, button=None):
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    point = QPointF(x, y)
    button = button or Qt.MouseButton.LeftButton
    return QMouseEvent(kind, point, point, button, button, Qt.KeyboardModifier.NoModifier)


def _arranged_strip(page):
    page.desktop_check.setChecked(True)
    page.create_home()
    page.strip_action("arrange", "")
    strip = page.strip_list[0]
    world = page.service.world
    desk = next(piece for piece in world.furniture.values() if piece.definition == "desk_basic")
    rect = strip.piece_rect(desk, world.definition(desk))
    return strip, world, desk, rect


def test_dragging_furniture_on_the_desktop_strip_moves_it(page):
    from PySide6.QtCore import QEvent
    strip, world, desk, rect = _arranged_strip(page)
    start = desk.cell
    x, y = rect.center().x(), rect.center().y()
    target = x + 4 * strip.cell_width()
    strip.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, x, y))
    assert page.selected_furniture == desk.identifier
    strip.mouseMoveEvent(_mouse(QEvent.Type.MouseMove, target, y))
    assert strip.preview is not None and strip.preview[1] == start + 4
    strip.mouseReleaseEvent(_mouse(QEvent.Type.MouseButtonRelease, target, y))
    assert world.furniture[desk.identifier].cell == start + 4
    assert strip.preview is None
    page.layout_panel.undo()
    assert any(piece.definition == "desk_basic" and piece.cell == start for piece in world.furniture.values())


def test_a_cancelled_strip_drag_leaves_the_piece_where_it_was(page):
    from PySide6.QtCore import QEvent
    strip, world, desk, rect = _arranged_strip(page)
    start = desk.cell
    x, y = rect.center().x(), rect.center().y()
    strip.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, x, y))
    strip.mouseMoveEvent(_mouse(QEvent.Type.MouseMove, x + 4 * strip.cell_width(), y))
    strip.hide()
    assert world.furniture[desk.identifier].cell == start
    assert strip.preview is None and page.view.preview is None


def test_clicking_a_piece_without_dragging_only_selects_it(page):
    from PySide6.QtCore import QEvent
    strip, world, desk, rect = _arranged_strip(page)
    start = desk.cell
    x, y = rect.center().x(), rect.center().y()
    strip.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, x, y))
    strip.mouseReleaseEvent(_mouse(QEvent.Type.MouseButtonRelease, x + 2, y))
    assert world.furniture[desk.identifier].cell == start
    assert page.selected_furniture == desk.identifier
