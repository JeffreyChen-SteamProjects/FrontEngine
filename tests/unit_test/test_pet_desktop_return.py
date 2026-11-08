"""Desktop pets come back on the next start: same identities, nothing to click."""
import json

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QColor, QPixmap

from frontengine.user_setting.desktop_pets import MAX_RETURNING, checked_returning


def _sprite(folder, name='sprite.png'):
    path = folder / name
    image = QPixmap(64, 64)
    image.fill(QColor('#d3a231'))
    assert image.save(str(path))
    return str(path)


def _spawn(page, path, count):
    page.pet_image_path = path
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


def test_pets_on_the_desktop_come_back_on_the_next_start(make_main_window, tmp_path, monkeypatch):
    window = _first_window(make_main_window, monkeypatch)
    identifiers = _spawn(window.pet_setting_ui, _sprite(tmp_path), 2)
    window.close()
    stored = json.loads((tmp_path / 'user_setting.json').read_text(encoding='utf-8'))
    assert [entry['id'] for entry in stored['pet_desktop_pets']] == identifiers
    again = _restart(make_main_window, tmp_path, monkeypatch)
    assert [pet.profile_session.identifier for pet in again.pet_setting_ui.pet_list] == identifiers


def test_a_pet_put_away_before_quitting_stays_away(make_main_window, tmp_path, monkeypatch):
    window = _first_window(make_main_window, monkeypatch)
    identifiers = _spawn(window.pet_setting_ui, _sprite(tmp_path), 2)
    window.pet_setting_ui.pet_list[0].close()
    window.close()
    again = _restart(make_main_window, tmp_path, monkeypatch)
    assert [pet.profile_session.identifier for pet in again.pet_setting_ui.pet_list] == identifiers[1:]


def test_turning_the_option_off_keeps_the_desktop_empty(make_main_window, tmp_path, monkeypatch):
    window = _first_window(make_main_window, monkeypatch)
    _spawn(window.pet_setting_ui, _sprite(tmp_path), 1)
    assert window.pet_setting_ui.return_checkbox.isChecked()
    window.pet_setting_ui.return_checkbox.setChecked(False)
    window.close()
    again = _restart(make_main_window, tmp_path, monkeypatch)
    assert again.pet_setting_ui.pet_list == []
    assert not again.pet_setting_ui.return_checkbox.isChecked()


def test_a_pet_whose_identity_is_busy_or_whose_picture_is_gone_is_skipped(make_main_window, tmp_path,
                                                                          monkeypatch):
    window = _first_window(make_main_window, monkeypatch)
    kept = _sprite(tmp_path)
    gone = _sprite(tmp_path, 'gone.png')
    identifiers = _spawn(window.pet_setting_ui, kept, 1) + _spawn(window.pet_setting_ui, gone, 1)[1:]
    window.close()
    (tmp_path / 'gone.png').unlink()
    again = _restart(make_main_window, tmp_path, monkeypatch)
    assert [pet.profile_session.identifier for pet in again.pet_setting_ui.pet_list] == identifiers[:1]


@pytest.mark.parametrize('value', [None, 'x', {}, [1], [{'id': 'A' * 32, 'path': 'p'}], [{'id': 'a' * 32}],
                                   [{'id': 'a' * 32, 'path': 3}], [{'id': 'a' * 32, 'path': 'p', 'x': 1}]])
def test_malformed_records_are_dropped_at_the_boundary(value):
    assert checked_returning(value) == []


def test_records_are_bounded_unique_and_need_an_existing_picture(tmp_path):
    picture = _sprite(tmp_path)
    entries = [{'id': f'{index:032x}', 'path': picture} for index in range(MAX_RETURNING + 3)]
    entries.insert(1, dict(entries[0]))
    entries.append({'id': 'f' * 32, 'path': str(tmp_path / 'missing.png')})
    checked = checked_returning(entries)
    assert len(checked) == MAX_RETURNING
    assert len({entry['id'] for entry in checked}) == MAX_RETURNING
