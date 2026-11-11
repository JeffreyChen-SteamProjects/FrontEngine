import pytest
from frontengine.user_setting.storage_session import StorageSession, StorageBusy, StorageClosed
from frontengine.user_setting.pet_game_save import HomeSaveStore
from frontengine.show.pet_game.home_service import HomeService
from frontengine.utils.pet_game.catalog import builtin_catalog


def test_duplicate_store_and_service_keep_first_owner(tmp_path):
    owner = StorageSession.open(tmp_path)
    store = HomeSaveStore(owner, builtin_catalog())
    service = HomeService(None, store, owner.profiles())
    try:
        catalog, records = builtin_catalog(), owner.profiles()
        with pytest.raises(StorageBusy):
            HomeSaveStore(owner, catalog)
        with pytest.raises(StorageBusy):
            HomeService(None, store, records)
        with pytest.raises(StorageBusy):
            owner.close()
    finally:
        service.shutdown()
        owner.close()


def test_closed_store_rejects_read_and_old_writer(tmp_path):
    owner = StorageSession.open(tmp_path)
    store = HomeSaveStore(owner, builtin_catalog())
    writer = store.write_encoded
    store.close()
    owner.close()
    successor = StorageSession.open(tmp_path)
    try:
        with pytest.raises(StorageClosed):
            store.load()
        with pytest.raises(StorageClosed):
            writer(b'{}')
        assert not (tmp_path / 'pet-home.json').exists()
    finally:
        successor.close()


def test_mode_switch_refusal_keeps_old_world_and_store(tmp_path):
    owner = StorageSession.open(tmp_path)
    store = HomeSaveStore(owner, builtin_catalog())
    service = HomeService(None, store, owner.profiles())
    blocked = HomeSaveStore(owner, builtin_catalog(), 'sandbox')
    try:
        world = service.create_home('screen', 0, 0, 12)
        assert service.switch_mode('sandbox') is None
        assert service.store is store
        assert service.world is world
    finally:
        blocked.close()
        service.shutdown()
        owner.close()


def test_home_alias_refuses_before_loading(tmp_path):
    import os
    owner = StorageSession.open(tmp_path)
    store = HomeSaveStore(owner, builtin_catalog())
    protected = tmp_path / 'protected'
    protected.write_text('{}')
    os.link(protected, tmp_path / 'pet-home.json')
    try:
        with pytest.raises(OSError):
            store.load()
        assert protected.read_text() == '{}'
    finally:
        store.close()
        owner.close()


def test_mode_transfer_reuses_shared_identity_and_preserves_failed_save(tmp_path, monkeypatch):
    owner = StorageSession.open(tmp_path)
    profiles = owner.profiles()
    pet = profiles.create('Shared')
    sandbox = HomeService(None, HomeSaveStore(owner, builtin_catalog(), 'sandbox'), profiles)
    sandbox.create_home('screen', 0, 0, 12)
    assert sandbox.adopt(pet['id']) == 'accepted'
    assert sandbox.shutdown()
    service = HomeService(None, HomeSaveStore(owner, builtin_catalog()), profiles)
    try:
        world = service.create_home('screen', 0, 0, 12)
        assert service.adopt(pet['id']) == 'accepted'
        session = service.sessions[pet['id']]
        with monkeypatch.context() as patch:
            patch.setattr(service.store, '_write', lambda *_: (_ for _ in ()).throw(PermissionError('disk')))
            assert service.switch_mode('sandbox') is None
            assert service.world is world
            assert service.sessions[pet['id']] is session
        assert service.switch_mode('sandbox').status == 'loaded'
        assert service.mode == 'sandbox'
        assert service.sessions[pet['id']] is session
        assert not session.care_timer.isActive()
        assert service.switch_mode('manage').status == 'loaded'
        assert service.sessions[pet['id']] is session
    finally:
        assert service.shutdown()
        owner.close()


def test_pending_target_cleanup_retains_claim_until_retry(tmp_path, monkeypatch):
    from frontengine.show.pet.pet_profile_session import PetProfileSession
    owner = StorageSession.open(tmp_path)
    profiles = owner.profiles()
    ids = sorted(profiles.create(name)['id'] for name in ('one', 'two', 'old'))
    target = HomeService(None, HomeSaveStore(owner, builtin_catalog(), 'sandbox'), profiles)
    target.create_home('screen', 0, 0, 12)
    for identifier in ids[:2]:
        assert target.adopt(identifier) == 'accepted'
    assert target.shutdown()
    service = HomeService(None, HomeSaveStore(owner, builtin_catalog()), profiles)
    world = service.create_home('screen', 0, 0, 12)
    assert service.adopt(ids[2]) == 'accepted'
    original_get = profiles.get
    failing = [False]
    def get(identifier):
        if failing[0] and identifier == ids[0]:
            raise PermissionError('staged cleanup read denied')
        return original_get(identifier)
    def construct(parent, identifier, records):
        if identifier == ids[1]:
            failing[0] = True
            raise PermissionError('target lease construction denied')
        return PetProfileSession(parent, identifier, records)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(profiles, 'get', get)
            patch.setattr(service, '_session_factory', construct)
            assert service.switch_mode('sandbox') is None
            assert service.world is world
            assert service.mode == 'manage'
            assert ids[2] in service.sessions
            catalog = builtin_catalog()
            with pytest.raises(StorageBusy):
                HomeSaveStore(owner, catalog, 'sandbox')
            assert service.shutdown() is False
        assert service.switch_mode('sandbox').status == 'loaded'
        assert service.mode == 'sandbox'
    finally:
        assert service.shutdown()
        owner.close()


def test_finalization_does_not_drop_identity_while_store_write_is_admitted(tmp_path, monkeypatch):
    from threading import Event, Thread
    owner = StorageSession.open(tmp_path)
    profiles = owner.profiles()
    identifier = profiles.create()['id']
    service = HomeService(None, HomeSaveStore(owner, builtin_catalog()), profiles)
    service.create_home('screen', 0, 0, 12)
    service.adopt(identifier)
    token = service._prepare_close()
    entered, release = Event(), Event()
    original = service.store._write
    def write(path, data):
        entered.set()
        assert release.wait(10)
        original(path, data)
    data = service.store.encode(service.world)
    monkeypatch.setattr(service.store, '_write', write)
    worker = Thread(target=service.store.write_encoded, args=(data,))
    try:
        worker.start()
        assert entered.wait(10)
        with pytest.raises(StorageBusy):
            token.finalize()
        assert identifier in service.sessions
        assert not service._closed
        release.set()
        worker.join(10)
        assert not worker.is_alive()
        token.finalize()
        assert service._closed
    finally:
        release.set()
        worker.join(10)
        service.shutdown()
        owner.close()


def test_resident_release_refusal_keeps_world_and_identity(tmp_path, monkeypatch):
    owner = StorageSession.open(tmp_path)
    profiles = owner.profiles()
    identifier = profiles.create()['id']
    service = HomeService(None, HomeSaveStore(owner, builtin_catalog()), profiles)
    service.create_home('screen', 0, 0, 12)
    service.adopt(identifier)
    session = service.sessions[identifier]
    try:
        with monkeypatch.context() as patch:
            patch.setattr(session, '_prepare_close', lambda: None)
            assert service.release(identifier) == 'save_failed'
            assert identifier in service.world.residents
            assert service.sessions[identifier] is session
        with monkeypatch.context() as patch:
            patch.setattr(service.world, 'remove_resident', lambda _identifier: 'refused')
            assert service.release(identifier) == 'refused'
            assert identifier in service.world.residents
            assert service.sessions[identifier] is session
            assert not session._closed
        assert service.release(identifier) == 'accepted'
        from frontengine.show.pet.pet_profile_session import PetProfileSession
        desktop = PetProfileSession(None, identifier, profiles)
        assert desktop.close()
    finally:
        service.shutdown()
        session.close()
        owner.close()


@pytest.mark.parametrize('retry_adoption', [False, True])
def test_rejected_adoption_retains_refused_cleanup_for_retry(tmp_path, monkeypatch, retry_adoption):
    from frontengine.show.pet.pet_profile_session import PetProfileSession
    owner = StorageSession.open(tmp_path)
    profiles = owner.profiles()
    identifier = profiles.create()['id']
    service = HomeService(None, HomeSaveStore(owner, builtin_catalog()), profiles)
    service.create_home('screen', 0, 0, 12)
    session = None
    try:
        with monkeypatch.context() as patch:
            patch.setattr(PetProfileSession, '_prepare_close', lambda self: None)
            assert service.adopt(identifier, zone='missing') == 'unavailable'
            session = PetProfileSession.active(profiles, identifier)
            assert identifier not in service.world.residents
            assert service.sessions.get(identifier) is session
            assert session is not None
            assert service.shutdown() is False
            with pytest.raises(StorageBusy):
                owner.close()
            if retry_adoption:
                assert service.adopt(identifier) == 'accepted'
                assert service.sessions[identifier] is session
        assert service.shutdown()
        assert PetProfileSession.active(profiles, identifier) is None
        desktop = PetProfileSession(None, identifier, profiles)
        assert desktop.close()
    finally:
        service.shutdown()
        if session is not None:
            session.close()
        owner.close()
