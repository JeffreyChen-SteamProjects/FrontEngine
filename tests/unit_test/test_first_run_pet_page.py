"""Someone with no pet yet starts on the page where one click puts a pet on the desktop."""
import json

from PySide6.QtCore import QCoreApplication


def _settle():
    for _ in range(5):
        QCoreApplication.processEvents()


def test_a_first_start_opens_on_the_pet_page(make_main_window):
    window = make_main_window()
    _settle()
    assert window.page_stack.currentWidget() is window.pet_setting_ui


def test_someone_with_a_pet_starts_where_they_always_did(make_main_window, tmp_path, monkeypatch, *, layered_pets):
    window = make_main_window()
    page = window.pet_setting_ui
    monkeypatch.setattr(page, '_target_geometry', lambda: None)
    layered_pets(page)
    page._spawn_pet()
    page.pet_list[0].close()                 # put away: the pet is not on the desktop, but it exists
    window.close()
    saved = json.loads((tmp_path / 'user_setting.json').read_text(encoding='utf-8'))
    again = make_main_window(saved)
    _settle()
    assert again.page_stack.currentWidget() is again.pet_home_ui


def test_someone_with_a_home_starts_on_the_home(make_main_window, tmp_path):
    window = make_main_window()
    window.pet_home_ui.create_home()
    window.close()
    saved = json.loads((tmp_path / 'user_setting.json').read_text(encoding='utf-8'))
    again = make_main_window(saved)
    _settle()
    assert again.page_stack.currentWidget() is again.pet_home_ui
