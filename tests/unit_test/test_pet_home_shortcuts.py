"""Stage shortcuts, the waiting list, zoom, the strip's way out of arranging and the newer-save button."""
import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtCore import QPoint

from frontengine.show.pet_game.home_service import HomeService
from frontengine.show.pet_game.home_view import ZOOMS
from frontengine.ui.page.pet_game.home_page import STAGE_HEIGHT, UPDATE_URL, PetHomePage
from frontengine.ui.page.pet_game.home_pending import MAX_PENDING, pending
from frontengine.user_setting.pet_game_save import HomeSaveStore
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.world import World


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
    from frontengine.user_setting.user_setting_file import user_setting_dict
    for key, value in (("pet_home_running", False), ("pet_home_on_desktop", True)):
        monkeypatch.setitem(user_setting_dict, key, value)


@pytest.fixture
def page(tmp_path):
    service = HomeService(None, HomeSaveStore(tmp_path, builtin_catalog()), PetProfiles({}, lambda: None))
    widget = PetHomePage(service)
    widget.resize(1200, 900)
    widget.show()
    yield widget
    widget.shutdown()
    widget.deleteLater()


def test_waiting_list_names_what_the_home_cannot_settle(page):
    page.create_home()
    world = page.service.world
    assert len(world.residents) == 1                                          # a first pet came along
    assert not any("move a pet" in text.lower() for text, _key in pending(world))
    empty = World(builtin_catalog(), "c" * 32, seed=1)
    empty.add_zone("s", 0, 0, 20)
    assert any("pet" in text.lower() for text, _key in pending(empty))        # an empty home asks for one
    world.ledger.apply("gift", "test", 500)
    world.buy("armchair", "t1")                                               # left in storage
    keys = [key for _text, key in pending(world, unread=3)]
    assert "pet_home_inbox_section" in keys
    assert "pet_home_layout_section" in keys
    assert len(pending(world, unread=3)) <= MAX_PENDING
    page.refresh()
    assert page.pending_list.count() >= 1
    page.pending_list.itemClicked.emit(page.pending_list.item(0))
    assert page.tabs.currentIndex() >= 0
    assert pending(None) == []


def test_shortcuts_open_their_tabs_and_step_aside(page):
    page.create_home()
    page.backpack_button.click()
    assert page.tabs.keys()[page.tabs.currentIndex()] == "pet_home_storage_section"
    page.goals_button.click()
    assert page.tabs.keys()[page.tabs.currentIndex()] == "pet_home_goals_section"
    asked = []
    page.desktop_requested.connect(lambda: asked.append(True))
    page.desktop_button.click()
    assert asked


def test_zoom_widens_and_heightens_the_stage_within_its_limits(page):
    page.create_home()
    width = page.view.minimumWidth()
    page.zoom_in.click()
    assert page.view.zoom == ZOOMS[1]
    assert page.view.minimumWidth() > width
    assert page.view.height() == round(STAGE_HEIGHT * ZOOMS[1])
    for _ in range(6):
        page.view.step_zoom(1)
    assert page.view.zoom == ZOOMS[-1]
    assert not page.zoom_in.isEnabled()
    wheel = QWheelEvent(QPointF(50, 50), QPointF(50, 50), QPoint(0, 0), QPoint(0, -120),
                        Qt.MouseButton.NoButton, Qt.KeyboardModifier.ControlModifier, Qt.ScrollPhase.NoScrollPhase, False)
    page.view.wheelEvent(wheel)
    assert page.view.zoom == ZOOMS[-2]
    page.view.set_zoom(0.1)
    assert page.view.zoom == ZOOMS[0]
    assert not page.zoom_out.isEnabled()


def test_the_strip_offers_a_way_out_of_arranging(page):
    page.create_home()
    strip = page.strip_list[0]
    assert strip.done_button.isHidden()
    page.layout_panel.toggle_arrange()
    assert not strip.done_button.isHidden()
    assert strip.done_button.focusPolicy() == Qt.FocusPolicy.NoFocus
    strip.done_button.click()
    assert not page.layout_panel.arranging
    assert strip.done_button.isHidden()


def test_a_newer_save_offers_the_update(tmp_path):
    (tmp_path / "pet-home.json").write_text('{"format": "frontengine.pet-home", "version": 999}', encoding="utf-8")
    service = HomeService(None, HomeSaveStore(tmp_path, builtin_catalog()), PetProfiles({}, lambda: None))
    page = PetHomePage(service)
    page.show()
    try:
        assert page.load_result.status == "newer"
        assert not page.update_button.isHidden()
        assert page.create_button.isHidden()
        assert UPDATE_URL.startswith("https://")
    finally:
        page.shutdown()
        page.deleteLater()
