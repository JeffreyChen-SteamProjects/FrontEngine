"""Arranging a zone: undo and redo, layout codes, ready-made layouts, dragging and nudging."""
import json

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QGuiApplication, QKeyEvent, QMouseEvent

from frontengine.show.pet_game.home_service import HomeService
from frontengine.ui.page.pet_game.home_page import PetHomePage
from frontengine.user_setting.pet_game_save import HomeSaveStore
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.multi_language.retranslate import translate
from frontengine.utils.pet_game import arrangement
from frontengine.utils.pet_game.catalog import builtin_catalog
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
def page(tmp_path, monkeypatch):
    from frontengine.user_setting.user_setting_file import user_setting_dict
    monkeypatch.setitem(user_setting_dict, "pet_home_running", False)
    service = HomeService(None, HomeSaveStore(tmp_path, builtin_catalog()), PetProfiles({}, lambda: None))
    widget = PetHomePage(service)
    widget.resize(1200, 900)
    widget.show()
    widget.create_home()
    yield widget
    widget.shutdown()
    widget.deleteLater()


def _mouse(kind, x, y):
    point = QPointF(x, y)
    return QMouseEvent(kind, point, point, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                       Qt.KeyboardModifier.NoModifier)


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
