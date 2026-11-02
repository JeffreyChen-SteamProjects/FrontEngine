"""Fewer steps: Start without a file opens the chooser, choosing or dropping a file shows it, the
overlay goes to FrontEngine's own screen without asking, an empty field is pointed at instead of a
warning dialog, Enter starts text and web pages, and a new home brings its first pet."""
import pytest
from PIL import Image
from PySide6.QtWidgets import QComboBox, QMessageBox, QWidget

from frontengine.ui.page import utils
from frontengine.ui.page.gif import gif_setting_ui
from frontengine.ui.page.image import image_setting_ui
from frontengine.ui.page.utils import (
    SPAN_ALL_DATA, build_target_monitor_combobox, dispatch_to_monitors, resolve_preferred_monitor,
)


@pytest.fixture(autouse=True)
def _no_dialogs(monkeypatch):
    """A flow that still stops on a dialog fails the test instead of hanging it."""
    def refuse(*_args, **_kwargs):
        raise AssertionError("a dialog was opened")
    monkeypatch.setattr(QMessageBox, "exec", refuse)
    monkeypatch.setattr(QMessageBox, "warning", refuse)
    monkeypatch.setattr(utils, "create_monitor_selection_dialog", refuse)


@pytest.fixture
def picture(tmp_path):
    path = tmp_path / "picture.png"
    Image.new("RGBA", (40, 30), (200, 80, 40, 255)).save(path)
    return str(path)


@pytest.fixture
def image_page():
    page = image_setting_ui.ImageSettingUI()
    yield page
    for widget in list(page.image_widget_list):
        widget.close()
    page.close()


def test_start_without_a_file_opens_the_chooser_and_shows_what_was_chosen(image_page, picture, monkeypatch):
    chosen = []
    monkeypatch.setattr(image_setting_ui, "choose_image", lambda _parent: chosen.append(1) or picture)
    image_page.start_play_image()
    assert chosen == [1]
    assert len(image_page.image_widget_list) == 1                 # one chooser, one overlay: no second click


def test_cancelling_the_chooser_shows_nothing_and_asks_nothing(image_page, monkeypatch):
    monkeypatch.setattr(image_setting_ui, "choose_image", lambda _parent: "")
    image_page.start_play_image()
    assert image_page.image_widget_list == []


def test_choosing_a_file_shows_it_at_once(picture, tmp_path, monkeypatch):
    animation = tmp_path / "a.gif"
    Image.new("RGB", (20, 20), "blue").save(animation)
    monkeypatch.setattr(gif_setting_ui, "choose_gif", lambda _parent: str(animation))
    page = gif_setting_ui.GIFSettingUI()
    try:
        page.choose_and_copy_file_to_cwd_gif_dir_then_play()
        assert len(page.gif_widget_list) == 1
    finally:
        for widget in list(page.gif_widget_list):
            widget.close()
        page.close()


def test_a_dropped_file_is_shown_at_once(image_page, picture):
    image_page._on_file_dropped(picture)
    assert len(image_page.image_widget_list) == 1


def test_this_screen_is_the_default_and_never_asks():
    combobox = build_target_monitor_combobox()
    assert combobox.currentData() is None
    host = QWidget()
    combobox.setParent(host)
    assert resolve_preferred_monitor(combobox) == 0                # the screen FrontEngine's window is on
    host.close()
    shown = []
    screens = ["left", "right"]
    dispatch_to_monitors(QWidget(), False, lambda monitor: QWidget(), lambda widget: None,
                         lambda widget, monitor, index: shown.append(monitor), preferred_monitor_index=1,
                         screens=screens)
    assert shown == ["right"]


def test_a_numbered_monitor_and_spanning_still_mean_what_they_say():
    combobox = QComboBox()
    combobox.addItem("here", None)
    combobox.addItem("1", 1)
    combobox.addItem("span", SPAN_ALL_DATA)
    combobox.setCurrentIndex(1)
    assert resolve_preferred_monitor(combobox) == 1
    combobox.setCurrentIndex(2)
    assert resolve_preferred_monitor(combobox) is None


def test_an_empty_text_points_at_its_field_and_enter_starts_it():
    from frontengine.ui.page.text.text_setting_ui import TextSettingUI
    page = TextSettingUI()
    page.show()
    try:
        page.start_draw_text_on_screen()
        assert page.text_widget_list == []
        assert page.line_edit.hasFocus() or page.line_edit.placeholderText()
        page.line_edit.setText("Hello")
        page.line_edit.returnPressed.emit()
        assert len(page.text_widget_list) == 1
    finally:
        for widget in list(page.text_widget_list):
            widget.close()
        page.close()


def test_an_empty_address_points_at_its_field_and_enter_is_wired():
    from frontengine.ui.page.web.web_setting_ui import WEBSettingUI
    page = WEBSettingUI()
    try:
        page.start_open_web_with_url()
        assert page.web_url_input.placeholderText()
        assert page.web_url_input.receivers("2returnPressed()") >= 1
    finally:
        page.close()


def test_a_new_home_without_pets_brings_a_first_one_and_selects_it(tmp_path, monkeypatch):
    from frontengine.show.pet_game.home_service import HomeService
    from frontengine.ui.page.pet_game.home_page import PetHomePage
    from frontengine.user_setting.pet_game_save import HomeSaveStore
    from frontengine.user_setting.pet_profiles import PetProfiles
    from frontengine.user_setting.user_setting_file import user_setting_dict
    from frontengine.utils.pet_game.catalog import builtin_catalog
    monkeypatch.setitem(user_setting_dict, "pet_home_on_desktop", False)
    profiles = PetProfiles({}, lambda: None)
    page = PetHomePage(HomeService(None, HomeSaveStore(tmp_path, builtin_catalog()), profiles))
    try:
        page.create_home()
        residents = page.service.world.residents
        assert len(residents) == 1
        assert page.selected_resident in residents
        assert len(profiles.profiles()) == 1
    finally:
        page.shutdown()
        page.close()
