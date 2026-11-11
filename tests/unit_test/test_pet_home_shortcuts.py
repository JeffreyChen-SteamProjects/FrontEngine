"""Stage shortcuts, the waiting list, zoom, the strip's way out of arranging and the newer-save button."""
import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtCore import QPoint

from frontengine.show.pet_game.home_service import HomeService
from frontengine.show.pet_game.home_view import ZOOMS
from frontengine.ui.page.pet_game.home_page import STAGE_HEIGHT, UPDATE_URL, PetHomePage
from frontengine.ui.page.pet_game.home_pending import MAX_PENDING, pending
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.world import World


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
    from frontengine.user_setting.user_setting_file import user_setting_dict
    for key, value in (("pet_home_running", False), ("pet_home_on_desktop", True)):
        monkeypatch.setitem(user_setting_dict, key, value)


@pytest.fixture
def page(tmp_path, *, home_store_factory, lifetime_factory):
    lifetime_factory()
    service = HomeService(None, home_store_factory(tmp_path, builtin_catalog()), PetProfiles({}, lambda: None))
    widget = PetHomePage(service, lifetime=lifetime_factory())
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


def test_a_newer_save_offers_the_update(tmp_path, *, home_store_factory, lifetime_factory):
    lifetime_factory()
    (tmp_path / "pet-home.json").write_text('{"format": "frontengine.pet-home", "version": 999}', encoding="utf-8")
    service = HomeService(None, home_store_factory(tmp_path, builtin_catalog()), PetProfiles({}, lambda: None))
    page = PetHomePage(service, lifetime=lifetime_factory())
    page.show()
    try:
        assert page.load_result.status == "newer"
        assert not page.update_button.isHidden()
        assert page.create_button.isHidden()
        assert UPDATE_URL.startswith("https://")
    finally:
        page.shutdown()
        page.deleteLater()


def _settle_reveal(page, rounds: int = 30) -> None:
    """Let the page finish laying out and scrolling: stop once nothing moved for three rounds."""
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QApplication
    content, still, last = page._scroll.widget(), 0, None
    for _ in range(rounds):
        QApplication.processEvents()
        now = (page._scroll.verticalScrollBar().value(), page.tabs.mapTo(content, QPoint(0, 0)).y())
        still = still + 1 if now == last else 0
        last = now
        if still >= 3:
            return


@pytest.mark.parametrize("height", [500, 900])
@pytest.mark.parametrize("target", ["backpack", "goals"])
@pytest.mark.parametrize("keyboard", [False, True])
def test_stage_shortcut_reveals_content_even_when_tab_is_already_selected(page, height, target, keyboard):
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    page.create_home()
    page.resize(1000, height)
    page.refresh()
    button = page.backpack_button if target == "backpack" else page.goals_button
    content = page.storage.list if target == "backpack" else page.goals.level
    for _ in range(3):
        QApplication.processEvents()
    for _ in range(2):
        page._scroll.verticalScrollBar().setValue(0)
        if keyboard:
            button.setFocus()
            QTest.keyClick(button, Qt.Key.Key_Space)
        else:
            button.click()
        _settle_reveal(page)
        assert not content.visibleRegion().isEmpty(), (target, height, keyboard)
        assert not page.tabs.tabBar().visibleRegion().isEmpty()


@pytest.mark.parametrize("route", ["pending", "strip"])
def test_home_navigation_links_reveal_their_target(page, route):
    from PySide6.QtWidgets import QApplication

    page.create_home()
    page.resize(1000, 500)
    page.inbox.add_error("Navigation fixture", page.service.world.time_ms)
    page.refresh()
    for _ in range(3):
        QApplication.processEvents()
    page._scroll.verticalScrollBar().setValue(0)
    if route == "pending":
        item = next(page.pending_list.item(i) for i in range(page.pending_list.count())
                    if page.pending_list.item(i).data(Qt.ItemDataRole.UserRole) == "pet_home_inbox_section")
        page.pending_list.itemClicked.emit(item)
    else:
        page.strip_list[0].action_requested.emit("tab", "pet_home_inbox_section")
    for _ in range(3):
        QApplication.processEvents()
    assert not page.inbox.list.visibleRegion().isEmpty()
    assert page.tabs.keys()[page.tabs.currentIndex()] == "pet_home_inbox_section"


def test_deferred_home_navigation_is_discarded_during_close_preparation(page):
    from PySide6.QtWidgets import QApplication

    page.create_home()
    page.resize(1000, 500)
    for _ in range(3):
        QApplication.processEvents()
    page._scroll.verticalScrollBar().setValue(0)
    page.backpack_button.click()
    page.lifetime.begin_prepare()
    try:
        for _ in range(3):
            QApplication.processEvents()
        assert page._scroll.verticalScrollBar().value() == 0
    finally:
        page.lifetime.cancel_prepare()
    for _ in range(3):
        QApplication.processEvents()
    assert page._scroll.verticalScrollBar().value() == 0
    page.backpack_button.click()
    for _ in range(3):
        QApplication.processEvents()
    assert not page.storage.list.visibleRegion().isEmpty()


@pytest.mark.parametrize("target", ["backpack", "goals"])
def test_shortcut_reveal_measures_after_content_above_settles(page, target):
    """A message above the tabs that shrinks just before the reveal must not push the tabs out of view."""
    from PySide6.QtWidgets import QApplication

    page.create_home()
    page.resize(1000, 500)
    page.refresh()
    page.report_text("\n".join(["A long message that takes room above the tabs."] * 12))
    for _ in range(3):
        QApplication.processEvents()
    page._scroll.verticalScrollBar().setValue(0)
    button = page.backpack_button if target == "backpack" else page.goals_button
    content = page.storage.list if target == "backpack" else page.goals.level
    button.click()
    page.report_text("")                      # the content above shrinks before the reveal runs
    _settle_reveal(page)
    assert not content.visibleRegion().isEmpty()
    assert not page.tabs.tabBar().visibleRegion().isEmpty()
