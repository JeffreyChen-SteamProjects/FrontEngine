"""Desktop pets come back on the next start: same identities, nothing to click."""
import json

import pytest
from PySide6.QtCore import QCoreApplication

from frontengine.user_setting.desktop_pets import MAX_RETURNING, checked_returning


def _spawn(page, ready, count):
    ready(page)
    for _ in range(count):
        page._spawn_pet()
    return [pet.profile_session.identifier for pet in page.pet_list]


def _restart(make_main_window, tmp_path, monkeypatch, **changes):
    saved = json.loads((tmp_path / 'user_setting.json').read_text(encoding='utf-8'))
    saved.update(changes)
    window = make_main_window(saved)
    monkeypatch.setattr(window.pet_setting_ui, '_target_geometry', lambda: None)
    for _ in range(5):
        QCoreApplication.processEvents()
    return window


def _first_window(make_main_window, monkeypatch):
    window = make_main_window()
    monkeypatch.setattr(window.pet_setting_ui, '_target_geometry', lambda: None)
    return window


def test_pets_on_the_desktop_come_back_on_the_next_start(make_main_window, tmp_path, monkeypatch, *, layered_pets):
    window = _first_window(make_main_window, monkeypatch)
    identifiers = _spawn(window.pet_setting_ui, layered_pets, 2)
    window.close()
    stored = json.loads((tmp_path / 'user_setting.json').read_text(encoding='utf-8'))
    assert stored['pet_desktop_pets'] == [{'id': identifier} for identifier in identifiers]   # identity only
    again = _restart(make_main_window, tmp_path, monkeypatch)
    assert [pet.profile_session.identifier for pet in again.pet_setting_ui.pet_list] == identifiers
    assert all(pet.profile_session.appearance_renderer is not None for pet in again.pet_setting_ui.pet_list)


def test_a_pet_put_away_before_quitting_stays_away(make_main_window, tmp_path, monkeypatch, *, layered_pets):
    window = _first_window(make_main_window, monkeypatch)
    identifiers = _spawn(window.pet_setting_ui, layered_pets, 2)
    window.pet_setting_ui.pet_list[0].close()
    window.close()
    again = _restart(make_main_window, tmp_path, monkeypatch)
    assert [pet.profile_session.identifier for pet in again.pet_setting_ui.pet_list] == identifiers[1:]


def test_turning_the_option_off_keeps_the_desktop_empty(make_main_window, tmp_path, monkeypatch, *, layered_pets):
    window = _first_window(make_main_window, monkeypatch)
    _spawn(window.pet_setting_ui, layered_pets, 1)
    assert window.pet_setting_ui.return_checkbox.isChecked()
    window.pet_setting_ui.return_checkbox.setChecked(False)
    window.close()
    again = _restart(make_main_window, tmp_path, monkeypatch)
    assert again.pet_setting_ui.pet_list == []
    assert not again.pet_setting_ui.return_checkbox.isChecked()


def test_an_old_picture_record_comes_back_as_its_character_and_a_deleted_pet_stays_away(
        make_main_window, tmp_path, monkeypatch, *, layered_pets):
    window = _first_window(make_main_window, monkeypatch)
    identifiers = _spawn(window.pet_setting_ui, layered_pets, 1)
    window.close()
    old = [{'id': identifiers[0], 'path': str(tmp_path / 'pet-previews' / 'inkside-mochi.png')},
           {'id': 'e' * 32, 'path': str(tmp_path / 'gone.gif')}]       # written before pets were layered only
    again = _restart(make_main_window, tmp_path, monkeypatch, pet_desktop_pets=old)
    assert [pet.profile_session.identifier for pet in again.pet_setting_ui.pet_list] == identifiers
    assert again.pet_setting_ui._waiting == []                          # nothing installs for the deleted one


@pytest.mark.parametrize('value', [None, 'x', {}, [1], [{'id': 'A' * 32}], [{'id': 'a' * 32, 'script': 's'}],
                                   [{'id': 'a' * 32, 'path': 3}], [{'id': 'a' * 32, 'path': 'p', 'x': 1}],
                                   [{'id': 'a' * 32, 'path': 'missing.puppet'}]])
def test_malformed_records_are_dropped_at_the_boundary(value):
    assert checked_returning(value) == []


def test_records_are_bounded_unique_and_keep_only_the_identity_of_a_layered_pet(tmp_path):
    picture = tmp_path / 'sprite.png'
    picture.write_bytes(b'x')
    entries = [{'id': f'{index:032x}'} for index in range(MAX_RETURNING + 3)]
    entries.insert(1, dict(entries[0]))
    entries.insert(2, {'id': 'f' * 32, 'path': str(picture)})          # an old picture record
    checked = checked_returning(entries)
    assert len(checked) == MAX_RETURNING
    assert len({entry['id'] for entry in checked}) == MAX_RETURNING
    assert checked[1] == {'id': 'f' * 32}
    assert all(set(entry) == {'id'} for entry in checked)

