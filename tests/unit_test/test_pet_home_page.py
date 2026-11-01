"""The Pet home page drives the first loop through the same service the app uses."""
import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent

from frontengine.show.pet_game.home_service import HomeService
from frontengine.ui.page.pet_game.home_page import PetHomePage
from frontengine.user_setting.pet_game_save import HomeSaveStore
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.multi_language.retranslate import translate
from frontengine.utils.pet_game.catalog import builtin_catalog


class Clock:
    def __init__(self) -> None:
        self.now = 50.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture(autouse=True)
def _running_setting(monkeypatch):
    from frontengine.user_setting.user_setting_file import user_setting_dict
    monkeypatch.setitem(user_setting_dict, "pet_home_running", False)


@pytest.fixture
def page(tmp_path):
    clock = Clock()
    service = HomeService(None, HomeSaveStore(tmp_path, builtin_catalog()), PetProfiles({}, lambda: None),
                          clock=clock)
    widget = PetHomePage(service)
    widget.clock = clock
    yield widget
    widget.shutdown()
    widget.deleteLater()


def _place(page, definition: str, cell: int) -> None:
    panel = page.layout_panel
    panel.storage.setCurrentIndex(panel.storage.findData(definition))
    panel.cell.setValue(cell)
    panel.place()


def test_no_home_offers_creation_and_disables_the_panels(page):
    assert page.service.world is None
    assert not page.create_button.isHidden() and page.run_button.isHidden()
    assert not page.residents.section.isEnabled()
    assert page.status.text() == translate("pet_home_create_hint")


def test_first_loop_from_the_page(page):
    page.create_home()
    assert page.service.world is not None and page.service.running
    assert page.residents.section.isEnabled()
    page.residents.new_pet()
    resident = page.selected_resident
    assert resident in page.service.world.residents
    for definition, cell in (("bed_basic", 2), ("table_basic", 7), ("desk_basic", 12)):
        _place(page, definition, cell)
    assert len(page.service.world.furniture) == 3
    assert page.layout_panel.storage.count() == 0
    page.work.units.setValue(2)
    page.work.assign()
    assert page.work.tasks.count() == 1
    for _ in range(1500):                   # five effective minutes
        page.clock.now += 0.2
        page.service._tick()
    assert page.service.world.ledger.coins >= 22
    assert page.residents.bars["energy"].value() == page.service.world.residents[resident].needs["energy"]
    page.shop.items.setCurrentIndex(page.shop.items.findData("plant_pot"))
    page.shop.buy()
    assert page.service.world.stored("plant_pot") == 1
    assert translate("pet_home_status").split("{")[0] in page.status.text()


def test_arranging_shows_reasons_and_escape_leaves(page):
    page.create_home()
    panel = page.layout_panel
    panel.toggle_arrange()
    panel.storage.setCurrentIndex(panel.storage.findData("bed_basic"))
    panel.cell.setValue(0)
    assert page.view.preview[3] == "entrance_blocked"
    panel.place()
    assert page.message.text() == translate("pet_home_result_entrance_blocked")
    page.view.cell_clicked.emit(5)
    assert panel.cell.value() == 5 and page.view.preview[3] is None
    page.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier))
    assert not panel.arranging and page.view.preview is None


def test_clicking_the_view_selects_residents_and_furniture(page):
    page.create_home()
    page.residents.new_pet()
    _place(page, "bed_basic", 4)
    page.view.resize(900, 180)
    resident = page.service.world.residents[page.selected_resident]
    page.select_resident(None)
    center = page.view.resident_center(resident)
    press = QMouseEvent(QEvent.Type.MouseButtonPress, center, center, Qt.MouseButton.LeftButton,
                        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    page.view.mousePressEvent(press)
    assert page.selected_resident == resident.identifier
    piece = next(iter(page.service.world.furniture.values()))
    rect = page.view.piece_rect(piece, page.service.world.definition(piece))
    point = QPointF(rect.center())
    page.view.mousePressEvent(QMouseEvent(QEvent.Type.MouseButtonPress, point, point, Qt.MouseButton.LeftButton,
                                          Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
    assert page.selected_furniture == piece.identifier
    page.residents.list.setCurrentRow(0)
    page.layout_panel.assign_bed()
    assert page.service.world.furniture[piece.identifier].owner == resident.identifier


def test_damaged_save_offers_recovery_without_overwriting(tmp_path):
    (tmp_path / "pet-home.json").write_text("{damaged", encoding="utf-8")
    service = HomeService(None, HomeSaveStore(tmp_path, builtin_catalog()), PetProfiles({}, lambda: None),
                          clock=Clock())
    page = PetHomePage(service)
    try:
        assert page.create_button.isHidden() and not page.aside_button.isHidden()
        assert page.status.text() == translate("pet_home_corrupt")
        page.create_home()
        assert service.world is None
        page.set_aside()
        assert (tmp_path / "pet-home.json").exists() is False
        assert not page.create_button.isHidden()
        page.create_home()
        assert service.world is not None
    finally:
        page.shutdown()
