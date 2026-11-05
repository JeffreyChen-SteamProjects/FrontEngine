"""Arranging a zone: undo and redo, layout codes, ready-made layouts, dragging and nudging."""
import json
from copy import deepcopy

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QGuiApplication, QKeyEvent, QMouseEvent

from frontengine.show.pet_game.home_service import HomeService
from frontengine.ui.page.pet_game.home_page import PetHomePage
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.multi_language.retranslate import translate
from frontengine.utils.pet_game import arrangement
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.resident import Activity
from frontengine.utils.pet_game.ledger import MAX_QUANTITY
from frontengine.utils.pet_game.world import World

CATALOG = builtin_catalog()


def _world(width=30, coins=0, mode="manage"):
    world = World(CATALOG, "a" * 32, mode, seed=3)
    zone = world.add_zone("screen", 0, 0, width)
    if mode == "manage":
        world.grant_starter_kit()
        world.furnish(zone)
        if coins:
            world.ledger.apply("gift", "test", coins)
    return world, zone


def test_undo_and_redo_restore_the_whole_zone():
    world, zone = _world()
    history = arrangement.LayoutHistory()
    before = arrangement.layout_of(world, zone)
    history.record(world, zone)
    bed = next(piece for piece in world.furniture.values() if piece.definition == "bed_basic")
    assert world.move(bed.identifier, 20) == "accepted"
    moved = arrangement.layout_of(world, zone)
    assert history.undo(world, zone)
    assert arrangement.layout_of(world, zone) == before
    assert history.redo(world, zone)
    assert arrangement.layout_of(world, zone) == moved
    assert not history.redo(world, zone)
    assert world.stored("bed_basic") == 0                         # nothing duplicated or lost


def test_undo_keeps_a_beds_owner():
    world, zone = _world()
    world.add_resident({"id": "b" * 32, "name": "Mochi", "mood": 60, "fullness": 60, "affection": 1,
                        "energy": 60}, zone)
    bed = next(piece for piece in world.furniture.values() if piece.definition == "bed_basic")
    world.assign_bed(bed.identifier, "b" * 32)
    history = arrangement.LayoutHistory()
    history.record(world, zone)
    world.store(bed.identifier)
    history.undo(world, zone)
    restored = next(piece for piece in world.furniture.values() if piece.definition == "bed_basic")
    assert restored.owner == "b" * 32


def test_blocked_undo_keeps_the_live_world_and_history_for_retry():
    world, zone = _world()
    other = world.add_zone("other", 0, 0, 30)
    history = arrangement.LayoutHistory()
    history.record(world, zone)
    bed = next(piece for piece in world.furniture.values() if piece.definition == "bed_basic")
    world.store(bed.identifier)
    result, moved = world.place("bed_basic", other, 1)
    assert result == "accepted"
    pet_id = "b" * 32
    world.add_resident({"id": pet_id, "name": "Pet", "mood": 80, "fullness": 80,
                        "affection": 0, "energy": 80}, zone)
    resident = world.residents[pet_id]
    table = next(piece for piece in world.furniture.values() if piece.definition == "table_basic")
    activity = resident.activity = Activity("eat", "test", furniture=table.identifier, phase="using")
    before = deepcopy(world.__dict__)
    pieces = dict(world.furniture)
    assert not history.undo(world, zone)
    assert world.next_id == before["next_id"]
    assert world.events == before["events"]
    assert world.progress == before["progress"]
    assert all(world.furniture[key] is piece for key, piece in pieces.items())
    assert world.residents[pet_id] is resident and resident.activity is activity
    assert activity == before["residents"][pet_id].activity
    assert history.can_undo() and not history.can_redo()
    world.store(moved)
    assert history.undo(world, zone)
    assert history.redo(world, zone)


def test_blocked_redo_keeps_its_step_until_inventory_returns():
    world, zone = _world()
    other = world.add_zone("other", 0, 0, 30)
    bed = next(piece for piece in world.furniture.values() if piece.definition == "bed_basic")
    world.store(bed.identifier)
    history = arrangement.LayoutHistory()
    history.record(world, zone)
    assert world.place("bed_basic", zone, 1)[0] == "accepted"
    assert history.undo(world, zone)
    result, moved = world.place("bed_basic", other, 1)
    assert result == "accepted"
    before = arrangement.snapshot(world, zone)
    assert not history.redo(world, zone)
    assert arrangement.snapshot(world, zone) == before
    assert history.can_redo() and not history.can_undo()
    world.store(moved)
    assert history.redo(world, zone)


def test_undo_after_room_shrinks_can_be_retried_when_it_fits():
    world, zone = _world(mode="sandbox")
    result, bed = world.place("bed_basic", zone, 25)
    assert result == "accepted"
    history = arrangement.LayoutHistory()
    history.record(world, zone)
    assert world.move(bed, 1) == "accepted"
    world.zones[zone].width_cells = 20
    assert not history.undo(world, zone)
    assert world.furniture[bed].cell == 1
    assert history.can_undo()
    world.zones[zone].width_cells = 30
    assert history.undo(world, zone)


def test_undo_refuses_storage_overflow_without_consuming_history():
    world = World(CATALOG, "a" * 32, "manage", seed=3)
    zone = world.add_zone("screen", 0, 0, 30)
    world.ledger.apply("stock", "test", items={"furniture:bed_basic": MAX_QUANTITY})
    history = arrangement.LayoutHistory()
    history.record(world, zone)
    assert world.place("bed_basic", zone, 1)[0] == "accepted"
    world.ledger.apply("refill", "test", items={"furniture:bed_basic": 1})
    assert not history.undo(world, zone)
    assert len(world.furniture) == 1 and history.can_undo()
    world.ledger.apply("free_space", "test", items={"furniture:bed_basic": -1})
    assert history.undo(world, zone)
    assert not world.furniture


def test_layout_codes_round_trip_and_reject_anything_else():
    world, zone = _world()
    code = arrangement.encode_layout(world, zone)
    assert arrangement.decode_layout(code, CATALOG) == arrangement.layout_of(world, zone)
    assert "ledger" not in code and "residents" not in code
    for bad in ("not json", json.dumps({"format": "other"}), json.dumps(
            {"format": arrangement.LAYOUT_FORMAT, "version": 1, "pieces": [["../../evil", 1, False]]}),
            json.dumps({"format": arrangement.LAYOUT_FORMAT, "version": 1, "pieces": [["bed_basic", "1", False]]}),
            "x" * (arrangement.MAX_LAYOUT_TEXT + 1)):
        with pytest.raises(ValueError):
            arrangement.decode_layout(bad, CATALOG)


def test_every_ready_made_layout_fits_and_reports_its_cost():
    for name, pieces in arrangement.PRESETS.items():
        world, zone = _world(width=24, coins=5000)
        missing, cost, unavailable = arrangement.plan(world, zone, pieces)
        assert cost == sum(CATALOG.furniture[key].price * count for key, count in missing.items()
                           if key not in unavailable), name
        result, skipped = arrangement.apply_layout(world, zone, pieces, "t-" + name, buy_missing=True)
        assert result == "accepted"
        assert skipped == sum(unavailable.values()), name
        assert world.ledger.coins == 5000 + 10 - cost, name


def test_applying_without_enough_coins_changes_nothing():
    world, zone = _world()
    before = arrangement.layout_of(world, zone)
    assert arrangement.apply_layout(world, zone, arrangement.PRESETS["cozy"], "t", buy_missing=True)[0] == \
        "insufficient_coins"
    assert arrangement.layout_of(world, zone) == before


@pytest.fixture
def page(tmp_path, monkeypatch, *, home_store_factory, lifetime_factory):
    from frontengine.user_setting.user_setting_file import user_setting_dict
    lifetime_factory()
    monkeypatch.setitem(user_setting_dict, "pet_home_running", False)
    service = HomeService(None, home_store_factory(tmp_path, builtin_catalog()), PetProfiles({}, lambda: None))
    widget = PetHomePage(service, lifetime=lifetime_factory())
    widget.resize(1200, 900)
    widget.show()
    widget.create_home()
    yield widget
    widget.shutdown()
    widget.deleteLater()


def _mouse(kind, x, y, button=Qt.MouseButton.LeftButton):
    point = QPointF(x, y)
    return QMouseEvent(kind, point, point, button, Qt.MouseButton.LeftButton,
                       Qt.KeyboardModifier.NoModifier)


def test_blocked_undo_reports_reason_and_keeps_retry_button(page):
    world, panel = page.service.world, page.layout_panel
    zone = page.zone
    other = world.add_zone("other", 0, 0, 30)
    panel.history.record(world, zone)
    bed = next(piece for piece in world.furniture.values() if piece.definition == "bed_basic")
    world.store(bed.identifier)
    result, moved = world.place("bed_basic", other, 1)
    assert result == "accepted"
    page.refresh()
    panel.undo_button.click()
    assert page.message.text() == translate("pet_home_result_layout_restore_blocked")
    assert panel.undo_button.isEnabled()
    world.store(moved)
    panel.undo_button.click()
    assert not panel.undo_button.isEnabled()
    assert panel.redo_button.isEnabled()


def test_dragging_a_piece_moves_it_and_can_be_undone(page):
    world, panel, view = page.service.world, page.layout_panel, page.view
    panel.toggle_arrange()
    desk = next(piece for piece in world.furniture.values() if piece.definition == "desk_basic")
    rect = view.piece_rect(desk, world.definition(desk))
    start = desk.cell
    view.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, rect.center().x(), rect.center().y()))
    target_x = rect.center().x() + 4 * view.cell_width()
    view.mouseMoveEvent(_mouse(QEvent.Type.MouseMove, target_x, rect.center().y()))
    assert view.preview is not None
    assert view.preview[3] is None
    view.set_world(world, page.zone)
    view.mouseReleaseEvent(_mouse(QEvent.Type.MouseButtonRelease, target_x, rect.center().y(),
                                  Qt.MouseButton.RightButton))
    assert desk.cell == start
    view.mouseReleaseEvent(_mouse(QEvent.Type.MouseButtonRelease, target_x, rect.center().y()))
    assert world.furniture[desk.identifier].cell == start + 4
    page.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.KeyboardModifier.NoModifier))
    assert world.furniture[desk.identifier].cell == start + 5
    page.layout_panel.undo()
    page.layout_panel.undo()
    assert any(piece.definition == "desk_basic" and piece.cell == start for piece in world.furniture.values())


def test_copy_paste_and_preview_on_the_page(page):
    panel = page.layout_panel
    panel.copy_layout()
    assert page.message.text() == translate("pet_home_result_layout_copied")
    panel.paste_layout()
    assert panel.presets.currentData() == "pasted"
    assert panel.layout_note.text() == translate("pet_home_layout_ready")
    QGuiApplication.clipboard().setText("hello")
    panel.paste_layout()
    assert page.message.text() == translate("pet_home_result_layout_invalid")
    panel.presets.setCurrentIndex(panel.presets.findData("cozy"))
    assert "—" in panel.layout_note.text()                          # what it needs and what it costs


@pytest.mark.parametrize('cancel', ['escape', 'reenable', 'hide', 'ungrab', 'zone'])
def test_cancelled_furniture_drag_does_not_move_piece(page, cancel):
    from PySide6.QtWidgets import QApplication

    world, panel, view = page.service.world, page.layout_panel, page.view
    panel.toggle_arrange()
    desk = next(piece for piece in world.furniture.values() if piece.definition == 'desk_basic')
    rect = view.piece_rect(desk, world.definition(desk))
    original = desk.cell
    target = rect.center().x() + 4 * view.cell_width()
    view.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, rect.center().x(), rect.center().y()))
    view.mouseMoveEvent(_mouse(QEvent.Type.MouseMove, target, rect.center().y()))
    assert view.preview is not None
    if cancel in ('escape', 'reenable'):
        page.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier))
        if cancel == 'reenable':
            panel.toggle_arrange()
    elif cancel == 'hide':
        view.hide()
        view.show()
    elif cancel == 'ungrab':
        QApplication.sendEvent(view, QEvent(QEvent.Type.UngrabMouse))
    else:
        other = world.add_zone('another', 0, 0, 30)
        view.set_world(world, other)
    view.mouseReleaseEvent(_mouse(QEvent.Type.MouseButtonRelease, target, rect.center().y()))
    assert desk.cell == original
    assert view.preview is None


@pytest.mark.parametrize('cancel', ['disable', 'tag', 'zone', 'escape'])
def test_cancelled_area_stroke_does_not_paint(page, cancel):
    world, panel, view = page.service.world, page.layout_panel, page.view
    panel.area_tag.setCurrentIndex(panel.area_tag.findData('work'))
    panel.area_paint.setChecked(True)
    panel._area_tool_changed()
    width = view.cell_width()
    view.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, 2 * width + 2, view.height() - 10))
    view.mouseMoveEvent(_mouse(QEvent.Type.MouseMove, 6 * width + 2, view.height() - 10))
    if cancel == 'disable':
        panel.area_paint.setChecked(False)
        panel._area_tool_changed()
    elif cancel == 'tag':
        panel.area_tag.setCurrentIndex(panel.area_tag.findData('living'))
    elif cancel == 'escape':
        page.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier))
        assert not panel.area_paint.isChecked()
    else:
        other = world.add_zone('another', 0, 0, 30)
        view.set_world(world, other)
    view.mouseReleaseEvent(_mouse(QEvent.Type.MouseButtonRelease, 6 * width + 2, view.height() - 10))
    assert all(not zone.areas for zone in world.zones.values())


def test_undo_history_belongs_to_its_room(page):
    world, panel = page.service.world, page.layout_panel
    first = page.zone
    second = world.add_zone('second', 1280, 0, 30)
    bed = next(piece for piece in world.furniture.values() if piece.definition == 'bed_basic')
    assert world.store(bed.identifier) == 'accepted'
    assert world.place('bed_basic', second, 3)[0] == 'accepted'
    before_first = arrangement.layout_of(world, first)
    before_second = arrangement.layout_of(world, second)
    desk = next(piece for piece in world.furniture.values() if piece.definition == 'desk_basic')
    assert panel._change(lambda current: current.move(desk.identifier, desk.cell + 4)) == 'accepted'
    after_first = arrangement.layout_of(world, first)
    page.choose_zone(second)
    panel.undo()
    assert arrangement.layout_of(world, second) == before_second
    page.choose_zone(first)
    panel.undo()
    assert arrangement.layout_of(world, first) == before_first
    page.choose_zone(second)
    panel.redo()
    assert arrangement.layout_of(world, second) == before_second
    page.choose_zone(first)
    panel.redo()
    assert arrangement.layout_of(world, first) == after_first


def test_switching_save_modes_does_not_reuse_layout_history(page):
    panel = page.layout_panel
    desk = next(piece for piece in page.service.world.furniture.values() if piece.definition == 'desk_basic')
    panel._change(lambda current: current.move(desk.identifier, desk.cell + 4))
    assert page.set_free_arranging(True)
    page.create_home()
    world, zone = page.service.world, page.zone
    before = arrangement.layout_of(world, zone)
    panel.undo()
    assert arrangement.layout_of(world, zone) == before
