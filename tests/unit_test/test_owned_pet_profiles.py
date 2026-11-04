import copy
import json
import os
from threading import Event, Thread

import pytest

from frontengine.show.pet.pet_profile_session import PetProfileSession
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.user_setting.storage_session import StorageBusy, StorageClosed, StorageSession
from frontengine.utils.json.json_repository import JsonRepository


def test_owned_profiles_are_cached_and_old_adapter_cannot_touch_successor(tmp_path):
    owner = StorageSession.open(tmp_path)
    profiles = owner.profiles()
    assert owner.profiles() is profiles
    record = profiles.create("First")
    borrowed = profiles.settings
    owner.close()
    successor = StorageSession.open(tmp_path)
    try:
        successor.profiles().update(record['id'], {'name': 'Latest'})
        old = copy.deepcopy(borrowed)
        disk = (tmp_path / 'user_setting.json').read_bytes()
        actions = [lambda: profiles.get(record['id']), profiles.profiles,
                   lambda: profiles.create('Old'), lambda: profiles.update(record['id'], {'name': 'Old'}),
                   lambda: profiles.import_profile(tmp_path / 'missing.json'),
                   lambda: profiles.export_profile(record['id'], tmp_path / 'export.json'), profiles.save]
        for action in actions:
            with pytest.raises(StorageClosed):
                action()
        assert borrowed == old
        assert (tmp_path / 'user_setting.json').read_bytes() == disk
        assert not (tmp_path / 'export.json').exists()
    finally:
        successor.close()


@pytest.mark.parametrize('name', ['user_setting.json', 'USER_SETTING.JSON', 'pet-home.json',
                                 'pet-home-sandbox.json.bak', 'pet-home.json.bak.tmp',
                                 '.frontengine-owner.lock', 'user_setting.json.tmp'])
def test_profile_export_refuses_managed_names_even_outside_owner(tmp_path, name):
    profiles = PetProfiles({}, lambda: None)
    record = profiles.create()
    destination = tmp_path / name
    destination.write_bytes(b'protected')
    with pytest.raises((OSError, ValueError)):
        profiles.export_profile(record['id'], destination)
    assert destination.read_bytes() == b'protected'


@pytest.mark.skipif(os.name != 'nt', reason='Win32 path aliases')
@pytest.mark.parametrize('name', ['user_setting.json.', 'user_setting.json ', 'user_setting.json:stream',
                                 'export.json:stream', 'export.json.'])
def test_profile_export_refuses_win32_aliases(tmp_path, name):
    profiles = PetProfiles({}, lambda: None)
    record = profiles.create()
    original = tmp_path / 'user_setting.json'
    original.write_bytes(b'protected')
    with pytest.raises((OSError, ValueError)):
        profiles.export_profile(record['id'], tmp_path / name)
    assert original.read_bytes() == b'protected'


@pytest.mark.parametrize('temporary', [False, True])
def test_export_refuses_hardlinked_destination_or_temp(tmp_path, temporary):
    profiles = PetProfiles({}, lambda: None)
    record = profiles.create()
    protected = tmp_path / 'important.json'
    protected.write_bytes(b'protected')
    destination = tmp_path / 'pet.json'
    os.link(protected, tmp_path / 'pet.json.tmp' if temporary else destination)
    with pytest.raises(OSError):
        profiles.export_profile(record['id'], destination)
    assert protected.read_bytes() == b'protected'
    if temporary:
        assert not destination.exists()
    else:
        assert destination.read_bytes() == b'protected'


def test_owned_pet_retains_owner_through_failed_and_canceled_close(tmp_path, monkeypatch):
    owner = StorageSession.open(tmp_path)
    profiles = owner.profiles()
    pet = PetProfileSession(None, profiles=profiles)
    try:
        with pytest.raises(StorageBusy):
            owner.close()
        pet.companion.mood.pet(1)
        with monkeypatch.context() as patch:
            patch.setattr(profiles, 'save', lambda: (_ for _ in ()).throw(PermissionError('disk')))
            assert not pet.close()
            with pytest.raises(StorageBusy):
                owner.close()
        prepared = pet._prepare_close()
        assert prepared is not None
        with pytest.raises(StorageBusy):
            owner.close()
        prepared.cancel()
        with pytest.raises(StorageBusy):
            owner.close()
        prepared = pet._prepare_close()
        with monkeypatch.context() as patch:
            patch.setattr(profiles, 'save', lambda: pytest.fail('Finalization wrote again'))
            prepared.finalize()
            prepared.finalize()
        owner.close()
    finally:
        pet.close()
        owner.close()


def test_duplicate_and_failed_pet_constructor_release_only_their_own_use(tmp_path, monkeypatch):
    owner = StorageSession.open(tmp_path)
    profiles = owner.profiles()
    pet = PetProfileSession(None, profiles=profiles)
    try:
        with pytest.raises(ValueError):
            PetProfileSession(None, pet.identifier, profiles)
        assert PetProfileSession.active(profiles, pet.identifier) is pet
        with pytest.raises(StorageBusy):
            owner.close()
        pet.close()
        import frontengine.show.pet.pet_profile_session as module
        with monkeypatch.context() as patch:
            patch.setattr(module, 'CompanionState', lambda *_: (_ for _ in ()).throw(ValueError('setup')))
            with pytest.raises(ValueError, match='setup'):
                PetProfileSession(None, profiles=profiles)
        owner.close()
    finally:
        pet.close()
        owner.close()


def test_profile_transaction_serializes_save_and_keeps_both_edits(tmp_path, monkeypatch):
    owner = StorageSession.open(tmp_path)
    profiles = owner.profiles()
    first, second = profiles.create('A'), profiles.create('B')
    entered, release, attempted = Event(), Event(), Event()
    failures = []
    original = JsonRepository.save

    def save(repository, data):
        if not entered.is_set():
            entered.set()
            assert release.wait(10)
        return original(repository, data)

    def update(identifier, name, signal=False):
        if signal:
            attempted.set()
        try:
            profiles.update(identifier, {'name': name})
        except BaseException as error:
            failures.append(error)

    monkeypatch.setattr(JsonRepository, 'save', save)
    a = Thread(target=update, args=(first['id'], 'AA'))
    b = Thread(target=update, args=(second['id'], 'BB', True))
    try:
        a.start()
        assert entered.wait(10)
        b.start()
        assert attempted.wait(10)
        with pytest.raises(StorageBusy):
            owner.close()
        release.set()
        a.join(10)
        b.join(10)
        assert not a.is_alive() and not b.is_alive()
        assert failures == []
        records = json.loads((tmp_path / 'user_setting.json').read_text())['pet_profiles']['records']
        assert records[first['id']]['name'] == 'AA'
        assert records[second['id']]['name'] == 'BB'
    finally:
        release.set()
        a.join(10)
        if b.ident:
            b.join(10)
        owner.close()


def test_failed_profile_transaction_cannot_roll_back_another_committed_edit(tmp_path, monkeypatch):
    owner = StorageSession.open(tmp_path)
    profiles = owner.profiles()
    first, second = profiles.create('A'), profiles.create('B')
    entered, release, attempted, saved = Event(), Event(), Event(), Event()
    failures = []
    original = profiles.save

    def save():
        if not entered.is_set():
            entered.set()
            assert release.wait(10)
            raise PermissionError('first transaction fails')
        original()
        saved.set()

    def update(identifier, name, signal=False):
        if signal:
            attempted.set()
        try:
            profiles.update(identifier, {'name': name})
        except PermissionError:
            failures.append(name)

    monkeypatch.setattr(profiles, 'save', save)
    a = Thread(target=update, args=(first['id'], 'AA'))
    b = Thread(target=update, args=(second['id'], 'BB', True))
    try:
        a.start()
        assert entered.wait(10)
        b.start()
        assert attempted.wait(10)
        assert not saved.wait(0.1)
        release.set()
        a.join(10)
        b.join(10)
        assert not a.is_alive() and not b.is_alive()
        assert failures == ['AA']
        assert profiles.get(first['id'])['name'] == 'A'
        assert profiles.get(second['id'])['name'] == 'BB'
        records = json.loads((tmp_path / 'user_setting.json').read_text())['pet_profiles']['records']
        assert records[first['id']]['name'] == 'A'
        assert records[second['id']]['name'] == 'BB'
    finally:
        release.set()
        a.join(10)
        if b.ident:
            b.join(10)
        owner.close()


def test_independent_owners_allow_copied_identity_and_export_import(tmp_path):
    first = StorageSession.open(tmp_path / 'first')
    second = StorageSession.open(tmp_path / 'second')
    a = b = None
    try:
        record = first.profiles().create('Original')
        second.settings['pet_profiles'] = copy.deepcopy(first.settings['pet_profiles'])
        second.save_settings()
        a = PetProfileSession(None, record['id'], first.profiles())
        b = PetProfileSession(None, record['id'], second.profiles())
        assert PetProfileSession.active(first.profiles(), record['id']) is a
        assert PetProfileSession.active(second.profiles(), record['id']) is b
        exported = tmp_path / 'portable.json'
        first.profiles().export_profile(record['id'], exported)
        imported = second.profiles().import_profile(exported)
        assert imported['id'] != record['id']
        assert imported['name'] == record['name']
    finally:
        if a:
            a.close()
        if b:
            b.close()
        first.close()
        second.close()


def test_memory_profiles_keep_mapping_identity_reassignment_and_save_injection():
    original = {}
    profiles = PetProfiles(original, lambda: None)
    assert profiles.settings is original
    original_key = profiles.identity_key
    replacement = {}
    profiles.settings = replacement
    assert profiles.settings is replacement
    assert profiles.identity_key != original_key
    saved = []
    profiles.save = lambda: saved.append(copy.deepcopy(replacement))
    record = profiles.create('Injected')
    assert saved[-1]['pet_profiles']['records'][record['id']]['name'] == 'Injected'


@pytest.mark.parametrize('temporary', [False, True])
def test_export_refuses_linked_destination_or_writer_temp(tmp_path, temporary):
    profiles = PetProfiles({}, lambda: None)
    record = profiles.create()
    protected = tmp_path / 'important.json'
    protected.write_bytes(b'protected')
    destination = tmp_path / 'export.json'
    linked = tmp_path / 'export.json.tmp' if temporary else destination
    try:
        linked.symlink_to(protected)
    except OSError:
        pytest.skip('Symlink creation is unavailable')
    with pytest.raises(OSError):
        profiles.export_profile(record['id'], destination)
    assert protected.read_bytes() == b'protected'


def test_export_refuses_missing_managed_path_through_parent_alias(tmp_path):
    profiles = PetProfiles({}, lambda: None)
    record = profiles.create()
    parent = tmp_path / 'other'
    parent.mkdir()
    with pytest.raises(OSError):
        profiles.export_profile(record['id'], parent / '..' / 'pet-home.json')
    assert not (tmp_path / 'pet-home.json').exists()


def test_owned_profile_results_are_detached(tmp_path):
    owner = StorageSession.open(tmp_path)
    try:
        profiles = owner.profiles()
        created = profiles.create('Original')
        retrieved = profiles.get(created['id'])
        listed = profiles.profiles()[0]
        for record in (created, retrieved, listed):
            record['appearance']['saved_outfits'].append({'bad': True})
            record['preferences']['auto_rest'] = False
        saved = profiles.get(created['id'])
        assert saved['appearance']['saved_outfits'] == []
        assert saved['preferences']['auto_rest'] is True
    finally:
        owner.close()


@pytest.mark.skipif(os.name != 'nt', reason='Native Windows short filename aliases')
def test_export_refuses_actual_short_filename_alias(tmp_path):
    import ctypes
    from ctypes import wintypes
    get_short = ctypes.WinDLL('kernel32', use_last_error=True).GetShortPathNameW
    get_short.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    get_short.restype = wintypes.DWORD
    protected = tmp_path / 'user_setting.json'
    protected.write_bytes(b'protected')
    buffer = ctypes.create_unicode_buffer(32768)
    length = get_short(str(protected), buffer, len(buffer))
    assert 0 < length < len(buffer)
    from pathlib import Path
    alias = Path(buffer.value)
    if alias.name.casefold() == protected.name.casefold():
        pytest.skip('This volume does not generate short filename aliases')
    assert alias.read_bytes() == b'protected'
    profiles = PetProfiles({}, lambda: None)
    record = profiles.create()
    with pytest.raises(OSError):
        profiles.export_profile(record['id'], alias)
    assert protected.read_bytes() == b'protected'
