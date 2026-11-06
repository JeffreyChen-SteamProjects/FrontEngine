"""The Pet home page drives the first loop through the same service the app uses."""
import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent

from frontengine.show.pet_game.home_service import HomeService
from frontengine.ui.page.pet_game.home_page import PetHomePage
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
def page(tmp_path, *, home_store_factory, lifetime_factory):
    lifetime_factory()
    clock = Clock()
    service = HomeService(None, home_store_factory(tmp_path, builtin_catalog()), PetProfiles({}, lambda: None),
                          clock=clock)
    widget = PetHomePage(service, lifetime=lifetime_factory())
    widget.clock = clock
    yield widget
    widget.shutdown()
    widget.close()
    widget.deleteLater()
    widget.deleteLater()


def _place(page, definition: str, cell: int) -> None:
    """Choose the stored piece and click the floor while arranging, as a player does."""
    panel = page.layout_panel
    assert panel.storage.select_key(definition)
    if not panel.arranging:
        panel.toggle_arrange()
    page.view.cell_clicked.emit(cell)
    panel.toggle_arrange()


def test_work_list_accessible_name_follows_language(page):
    from PySide6.QtGui import QAccessible
    from frontengine.ui.menu.language_menu import LANGUAGES
    from frontengine.utils.multi_language.language_wrapper import language_wrapper
    from frontengine.utils.multi_language.retranslate import retranslator

    interface = QAccessible.queryAccessibleInterface(page.work.tasks)
    assert interface is not None
    try:
        for _label, language in LANGUAGES:
            assert language_wrapper.reset_language(language)
            retranslator.apply()
            expected = translate('pet_home_work_section', 'Work')
            assert expected
            assert interface.text(QAccessible.Text.Name) == expected
    finally:
        language_wrapper.reset_language('English')
        retranslator.apply()


def test_styled_home_keeps_requested_width_in_every_language(page, request):
    import os
    from pathlib import Path
    from PySide6.QtGui import QFontDatabase, QFontInfo
    from PySide6.QtWidgets import QApplication
    from frontengine.ui.style.app_style import apply_app_style
    from frontengine.utils.multi_language.language_wrapper import language_wrapper
    from frontengine.utils.multi_language.retranslate import retranslator

    font_file = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts/arial.ttf'
    if not font_file.is_file():
        pytest.skip('Windows Arial regression fixture is unavailable')
    identifier = QFontDatabase.addApplicationFont(str(font_file))
    assert identifier >= 0
    request.addfinalizer(lambda: QFontDatabase.removeApplicationFont(identifier))
    font = page.font()
    font.setFamily('Arial')
    page.setFont(font)
    assert QFontInfo(page.font()).family() == 'Arial'
    apply_app_style(page, None)
    page.show()
    page.create_home()
    try:
        for width in (296, 536):
            for language in language_wrapper.choose_language_dict:
                assert language_wrapper.reset_language(language)
                retranslator.apply()
                page.refresh()
                page.resize(width, 760)
                for key in page.tabs.keys():
                    assert page.tabs.select(key)
                    for _ in range(3):
                        QApplication.processEvents()
                    assert page.width() == width, (language, key, page.width())
                    assert page._scroll.horizontalScrollBar().maximum() == 0, (language, key)
    finally:
        language_wrapper.reset_language('English')
        retranslator.apply()


def test_new_day_replaces_visible_commissions_without_another_event(page):
    from frontengine.show.pet_game.captions import item_label
    from frontengine.utils.pet_game import simulation
    from frontengine.utils.pet_game.schedule import DAY_MS

    page.create_home()
    world = page.service.world
    world.home = "00000000000000000000000000000001"
    world.automatic = False
    for resident in world.residents.values():
        resident.parked = True
    world.progress.commissions["day"] = 0
    world.time_ms = DAY_MS - simulation.STEP_MS
    world.progress.next_check_ms = DAY_MS
    page.refresh()
    yesterday = [page.goals.commissions.item(i).text() for i in range(page.goals.commissions.count())]
    world.drain_events()

    page.service.run(lambda current: simulation.advance(current, simulation.STEP_MS))

    assert world.progress.commissions["day"] == 2
    expected = [translate("pet_home_offer_line", "{count} × {item} → {coins} coins").format(
        count=offer["count"], item=item_label(world, offer["item"]), coins=offer["coins"])
        for offer in world.progress.commissions["offers"]]
    assert expected != yesterday
    assert [page.goals.commissions.item(i).text() for i in range(page.goals.commissions.count())] == expected


def test_no_home_offers_creation_and_disables_the_panels(page):
    assert page.service.world is None
    assert not page.create_button.isHidden()
    assert page.run_button.isHidden()
    assert not page.residents.section.isEnabled()
    assert page.status.text() == translate("pet_home_create_hint")


@pytest.mark.parametrize('operation', ['move', 'result', 'photo', 'blueprint', 'save_error'])
def test_operation_message_follows_language_without_losing_values(page, tmp_path, monkeypatch, operation):
    from PySide6.QtGui import QPixmap
    from frontengine.utils.multi_language.language_wrapper import language_wrapper
    from frontengine.utils.multi_language.retranslate import retranslator

    language_wrapper.reset_language('English')
    retranslator.apply()
    page.create_home()
    values = {}
    if operation == 'move':
        key, values = 'pet_home_moved_in', {'count': 1}
    elif operation == 'result':
        page.report('pick_item')
        key = 'pet_home_result_pick_item'
    elif operation == 'photo':
        picture = QPixmap(8, 8)
        picture.fill(Qt.GlobalColor.white)
        target = page.goals.save_photo(picture, 'test')
        assert target.is_file()
        key, values = 'pet_home_photo_saved', {'path': target}
    elif operation == 'blueprint':
        target = tmp_path / 'maison-{original}.json'
        monkeypatch.setattr(page.layout_panel, 'choose_save_path', lambda: str(target))
        assert page.layout_panel.share_blueprint() == target
        key, values = 'pet_home_blueprint_saved', {'path': target}
    else:
        page.service.save_failed.emit('disk {original} unavailable')
        key, values = 'pet_home_save_failed', {'error': 'disk {original} unavailable'}
    before = page.message.text()
    try:
        assert language_wrapper.reset_language('France')
        retranslator.apply()
        assert page.message.text() == translate(key).format(**values)
        assert page.message.text() != before
        if operation == 'save_error':
            page.service.saved.emit()
            assert page.message.text() == ''
            assert page.message.isHidden()
    finally:
        language_wrapper.reset_language('English')
        retranslator.apply()


def test_raw_message_replaces_save_failure_and_survives_language_change(page):
    from frontengine.utils.multi_language.language_wrapper import language_wrapper
    from frontengine.utils.multi_language.retranslate import retranslator

    page.create_home()
    page.service.save_failed.emit('disk unavailable')
    raw = 'original diagnostic: {path} /tmp/échec.json'
    page.report_text(raw)
    try:
        assert language_wrapper.reset_language('France')
        retranslator.apply()
        page.service.saved.emit()
        assert page.message.text() == raw
        page.report_text('')
        language_wrapper.reset_language('English')
        retranslator.apply()
        assert page.message.text() == '' and page.message.isHidden()
    finally:
        language_wrapper.reset_language('English')
        retranslator.apply()


@pytest.mark.parametrize("failed_store", ["home", "profiles"])
def test_refused_shutdown_keeps_desktop_home_until_save_retry(page, monkeypatch, failed_store):
    page.create_home()
    page.desktop_check.setChecked(True)
    page.sync_strip()
    strips = list(page.strip_list)
    assert strips and all(strip.isVisible() for strip in strips)
    identities = set(page.service.sessions)
    next(iter(page.service.world.residents.values())).needs["energy"] -= 10

    def deny_save(*_args):
        raise PermissionError("disk unavailable")

    target = page.service.store if failed_store == "home" else page.service.profiles
    with monkeypatch.context() as patch:
        patch.setattr(target, "save", deny_save)
        assert page.shutdown() is False
        assert page.strip_list == strips
        assert all(strip.isVisible() for strip in strips)
        assert not page.art.closed
        assert set(page.service.sessions) == identities
        assert page.service.save_timer.isActive()

    assert page.service.save_now()
    assert page.message.isHidden()
    assert page.shutdown()
    assert not page.strip_list
    assert page.art.closed
    assert not page.service.sessions


def test_successful_save_clears_failure_banner_but_keeps_inbox(page):
    page.service.save_failed.emit("disk unavailable")
    assert "disk unavailable" in page.message.text()
    assert not page.message.isHidden()
    history = [page.inbox.list.item(i).text() for i in range(page.inbox.list.count())]
    assert history
    unread = page.inbox.unread

    page.service.saved.emit()

    assert page.message.text() == ""
    assert page.message.isHidden()
    assert [page.inbox.list.item(i).text() for i in range(page.inbox.list.count())] == history
    assert page.inbox.unread == unread


@pytest.mark.parametrize("same_text", [False, True])
def test_successful_save_preserves_a_newer_report(page, same_text):
    page.service.save_failed.emit("disk unavailable")
    text = page.message.text() if same_text else "Furniture placed."
    page.report_text(text)

    page.service.saved.emit()

    assert page.message.text() == text
    assert not page.message.isHidden()


def test_repeated_save_failures_clear_after_each_recovery(page):
    for _ in range(2):
        page.service.save_failed.emit("disk unavailable")
        page.service.save_failed.emit("disk unavailable")
        assert not page.message.isHidden()
        page.service.saved.emit()
        assert page.message.text() == ""
        assert page.message.isHidden()
        page.report_text("Furniture placed.")
        page.service.saved.emit()
        assert page.message.text() == "Furniture placed."
    assert page.inbox.unread == 4
    assert page.inbox.entries[0]["count"] == 4


def test_failed_mode_switch_clears_save_error_after_recovery(page, monkeypatch):
    page.create_home()

    def deny_save(_world):
        raise PermissionError("disk unavailable")

    with monkeypatch.context() as patch:
        patch.setattr(page.service.store, "save", deny_save)
        assert not page.set_free_arranging(True)
        assert page.service.mode == "manage"
        assert not page.sandbox_button.isChecked()
        assert page.message.text()

    assert page.service.save_now()
    assert page.message.text() == ""
    assert page.message.isHidden()
    assert page.service.mode == "manage"
    assert not page.sandbox_button.isChecked()


def test_profile_save_failure_keeps_banner_until_complete_retry(page, monkeypatch):
    page.create_home()
    resident = next(iter(page.service.world.residents.values()))
    resident.needs["energy"] -= 10
    saved = []
    page.service.saved.connect(lambda: saved.append(True))

    def deny_profile_save():
        raise PermissionError("profile disk unavailable")

    with monkeypatch.context() as patch:
        patch.setattr(page.service.profiles, "save", deny_profile_save)
        assert not page.set_free_arranging(True)
        assert page.message.text()
        assert not page.service.save_now()
        assert page.message.text()
        assert not saved
        assert page.service.save_timer.isActive()

    page.service.save_timer.timeout.emit()
    assert saved == [True]
    assert page.message.text() == ""
    assert page.message.isHidden()
    assert page.service.mode == "manage"
    profile = page.service.profiles.get(resident.identifier)
    assert profile["energy"] == resident.needs["energy"]


def test_first_loop_from_the_page(page):
    page.create_home()
    assert page.service.world is not None
    assert page.service.running
    assert page.residents.section.isEnabled()
    page.residents.new_pet()
    resident = page.selected_resident
    assert resident in page.service.world.residents
    assert len(page.service.world.furniture) == 3          # the starter kit is set out by itself
    assert page.layout_panel.storage.count() == 0
    for _ in range(1500):                   # five effective minutes: the pet takes up work by itself
        page.clock.now += 0.2
        page.service._tick()
    assert page.work.tasks.count() >= 1 or page.service.world.ledger.coins > 10
    assert page.service.world.ledger.coins >= 22
    assert page.residents.bars["energy"].value() == page.service.world.residents[resident].needs["energy"]
    assert page.shop.items.select_key("furniture:plant_pot")
    page.shop.buy()
    assert page.service.world.stored("plant_pot") == 0                 # bought straight into the home
    assert any(piece.definition == "plant_pot" for piece in page.service.world.furniture.values())
    assert translate("pet_home_status").split("{")[0] in page.status.text()


def test_arranging_shows_reasons_and_escape_leaves(page):
    page.create_home()
    world = page.service.world
    bed = next(piece.identifier for piece in world.furniture.values() if piece.definition == "bed_basic")
    page.service.run(lambda w: w.store(bed))
    page.refresh()
    panel = page.layout_panel
    panel.toggle_arrange()
    assert panel.storage.select_key("bed_basic")
    page.view.cell_clicked.emit(0)
    assert page.view.preview[3] == "entrance_blocked"
    assert page.message.text() == translate("pet_home_result_entrance_blocked")
    assert world.stored("bed_basic") == 1
    page.view.cell_clicked.emit(18)
    assert world.stored("bed_basic") == 0                       # placed where it was clicked
    assert any(p.definition == "bed_basic" and p.cell == 18 for p in world.furniture.values())
    page.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier))
    assert not panel.arranging
    assert page.view.preview is None


def test_clicking_the_view_selects_residents_and_furniture(page):
    page.create_home()
    # creating a home with no pets brings a first one
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


def test_damaged_save_offers_recovery_without_overwriting(tmp_path, *, home_store_factory, lifetime_factory):
    lifetime_factory()
    (tmp_path / "pet-home.json").write_text("{damaged", encoding="utf-8")
    service = HomeService(None, home_store_factory(tmp_path, builtin_catalog()), PetProfiles({}, lambda: None),
                          clock=Clock())
    page = PetHomePage(service, lifetime=lifetime_factory())
    try:
        assert page.create_button.isHidden()
        assert not page.aside_button.isHidden()
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


def test_a_wide_home_scrolls_instead_of_shrinking_its_cells(page):
    from frontengine.show.pet_game.home_view import MIN_CELL
    page.create_home()
    cells = page.service.world.zones[page.zone].width_cells
    assert page.view.minimumWidth() >= cells * MIN_CELL
    page.view.resize(page.view.minimumWidth(), page.view.height())
    assert page.view.cell_width() >= MIN_CELL


def test_work_is_taken_up_by_itself_and_the_backpack_sells(page):
    page.create_home()
    page.service.world.ledger.apply("gift", "test", 500)
    page.residents.new_pet()
    assert page.shop.items.select_key("furniture:workbench")
    page.shop.buy()
    assert any(p.definition == "workbench" for p in page.service.world.furniture.values())
    assert page.shop.items.select_key("wood")
    page.shop.buy()
    page.shop.buy()
    assert page.service.world.ledger.count("wood") == 2
    resident = page.service.world.residents[page.selected_resident]
    resident.traits = ("handy", "quiet")
    from frontengine.utils.pet_game import behaviour
    page.service.run(lambda world: behaviour.auto_task(world, resident))
    page.refresh()
    assert page.work.tasks.count() == 1
    assert not page.work.tasks.item(0).icon().isNull()
    page.service.world.ledger.apply("toys", "test", 0, {"toy": 1})
    page.refresh()
    assert page.storage.list.select_key("toy")
    coins = page.service.world.ledger.coins
    page.storage.sell()
    assert page.service.world.ledger.coins == coins + 24


def test_empty_work_page_explains_what_to_check(page):
    from PySide6.QtWidgets import QLabel, QPushButton
    page.create_home()
    panel = page.work
    labels = [label.text() for label in panel.section.findChildren(QLabel) if not label.isHidden()]
    assert translate("pet_home_work_empty", "No jobs yet. Check residents' routines, workstations and materials in the backpack.") in labels
    assert panel.tasks.isHidden()
    cancel = next(button for button in panel.section.findChildren(QPushButton)
                  if button.text() == translate("pet_home_cancel_task"))
    assert not cancel.isEnabled()


def test_cancel_job_requires_selection_and_returns_to_empty_state(page):
    from PySide6.QtWidgets import QPushButton
    page.create_home()
    world = page.service.world
    resident = next(iter(world.residents))
    status, identifier = world.create_task("letter", resident)
    assert status == "accepted"
    page.refresh()
    panel = page.work
    cancel = next(button for button in panel.section.findChildren(QPushButton)
                  if button.text() == translate("pet_home_cancel_task"))
    assert not cancel.isEnabled()
    assert not panel.tasks.isHidden()
    panel.tasks.setCurrentRow(0)
    assert cancel.isEnabled()
    panel.tasks.clearSelection()
    assert not cancel.isEnabled()
    panel.tasks.setCurrentRow(0)
    assert cancel.isEnabled()
    before = world.ledger.coins
    cancel.click()
    assert identifier not in world.tasks
    assert world.ledger.coins == before
    assert panel.tasks.isHidden()
    assert not cancel.isEnabled()


def test_selected_job_stops_being_cancellable_when_it_settles(page):
    from PySide6.QtWidgets import QPushButton
    page.create_home()
    world = page.service.world
    status, identifier = world.create_task("letter", next(iter(world.residents)))
    assert status == "accepted"
    page.refresh()
    panel = page.work
    panel.tasks.setCurrentRow(0)
    cancel = next(button for button in panel.section.findChildren(QPushButton)
                  if button.text() == translate("pet_home_cancel_task"))
    assert cancel.isEnabled()
    world.tasks[identifier].state = "settled"
    panel.refresh_live()
    assert not cancel.isEnabled()
    assert panel.tasks.count() == 1


@pytest.mark.parametrize("states", [("claimed",), ("skipped",), ("claimed", "skipped")])
def test_finished_tutorial_hides_skip_but_keeps_goals_reviewable(page, states):
    from PySide6.QtWidgets import QPushButton
    from frontengine.utils.pet_game import goals
    page.create_home()
    button = next(button for button in page.goals.section.findChildren(QPushButton)
                  if button.text() == translate("pet_home_skip_tutorial"))
    assert not button.isHidden()
    world = page.service.world
    for index, goal in enumerate(goals.TUTORIAL):
        world.progress.goals[goal.identifier] = states[index % len(states)]
    page.service.events_ready.emit([{"kind": "goal_claimed", "goal": "move_in", "coins": 5, "time": world.time_ms}])
    assert button.isHidden()
    assert page.goals.tutorial.count() >= len(goals.TUTORIAL)
    world.progress.goals.pop(goals.TUTORIAL[-1].identifier)
    page.refresh()
    assert not button.isHidden()


def test_skip_tutorial_hides_button_without_paying_rewards(page):
    from PySide6.QtWidgets import QPushButton
    from frontengine.utils.pet_game import goals
    page.create_home()
    button = next(button for button in page.goals.section.findChildren(QPushButton)
                  if button.text() == translate("pet_home_skip_tutorial"))
    coins = page.service.world.ledger.coins
    button.click()
    assert button.isHidden()
    assert page.service.world.ledger.coins == coins
    assert all(goals.goal_state(page.service.world, goal) == "skipped" for goal in goals.TUTORIAL)
    assert page.goals.tutorial.count() >= len(goals.TUTORIAL)


def test_failed_moveout_keeps_selection_for_retry(page, monkeypatch):
    from PySide6.QtWidgets import QPushButton

    page.create_home()
    resident = next(iter(page.service.world.residents.values()))
    pet = resident.identifier
    page.select_resident(pet)
    resident.needs['energy'] = 41
    original_save = page.service.profiles.save

    def fail_save():
        raise OSError('Settings write refused')

    monkeypatch.setattr(page.service.profiles, 'save', fail_save)
    button = next(b for b in page.residents.section.findChildren(QPushButton)
                  if b.text() == translate('pet_home_release', 'Move out'))
    button.click()
    monkeypatch.setattr(page.service.profiles, 'save', original_save)
    assert pet in page.service.world.residents
    assert pet in page.service.sessions
    assert page.selected_resident == pet
    button = next(b for b in page.residents.section.findChildren(QPushButton)
                  if b.text() == translate('pet_home_release', 'Move out'))
    assert button.isEnabled()
    button.click()
    assert pet not in page.service.world.residents
    assert pet not in page.service.sessions
    assert page.selected_resident is None
    assert page.service.profiles.get(pet)['energy'] == 41


@pytest.mark.parametrize('reason', ['active_elsewhere', 'full_saved', 'full_new'])
def test_failed_movein_keeps_resident_selection(page, reason):
    from PySide6.QtWidgets import QPushButton
    from frontengine.utils.pet_game.world import MAX_RESIDENTS

    page.create_home()
    service = page.service
    pet = next(iter(service.world.residents))
    if reason.startswith('full'):
        while len(service.world.residents) < MAX_RESIDENTS:
            record = service.profiles.create()
            assert service.adopt(record['id']) == 'accepted'
    record = service.profiles.create('Waiting pet')
    identifier = record['id']
    page.select_resident(pet)
    page.refresh()
    page.residents.profiles.setCurrentIndex(page.residents.profiles.findData(identifier))
    lease = service._session_factory(None, identifier, service.profiles) if reason == 'active_elsewhere' else None
    key, label = ('pet_home_new_resident', 'New pet') if reason == 'full_new' else ('pet_home_adopt', 'Move in')
    button = next(b for b in page.residents.section.findChildren(QPushButton)
                  if b.text() == translate(key, label))
    before = set(service.world.residents)
    try:
        button.click()
        assert set(service.world.residents) == before
        assert identifier not in service.sessions
        assert page.selected_resident == pet
        assert all(control.isEnabled() for control in page.residents.commands)
    finally:
        if lease is not None:
            assert lease.close()
