from threading import Event

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QRunnable, QThreadPool
from PySide6.QtWidgets import QLabel


def pump():
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QCoreApplication.processEvents()
    from PySide6.QtTest import QTest
    QTest.qWait(2)


def test_retired_callbacks_cannot_mutate_successor(tmp_path, monkeypatch):
    from frontengine.ui.runtime_lifetime import DefaultSettingsLifetime, CloseDisposition
    monkeypatch.chdir(tmp_path)
    lifetime = DefaultSettingsLifetime.open()
    calls = []
    callback = lifetime.guard(lambda: calls.append('old'))
    callback()
    assert lifetime.close() == CloseDisposition.DRAINING
    for _ in range(10):
        pump()
    assert lifetime.closed
    successor = DefaultSettingsLifetime.open()
    callback()
    assert calls == ['old']
    successor.close()
    for _ in range(10):
        pump()


def test_owned_jobs_hold_binding_but_unrelated_jobs_do_not(tmp_path, monkeypatch):
    from frontengine.ui.runtime_lifetime import DefaultSettingsLifetime
    from frontengine.user_setting.storage_session import StorageInUse, StorageSession
    monkeypatch.chdir(tmp_path)
    started, release, unrelated_started, unrelated_release = Event(), Event(), Event(), Event()
    class Job(QRunnable):
        def __init__(self, began, finish):
            super().__init__()
            self.began, self.finish = began, finish
        def run(self):
            self.began.set()
            assert self.finish.wait(10)
    lifetime = DefaultSettingsLifetime.open()
    lifetime.submit(Job(started, release))
    QThreadPool.globalInstance().start(Job(unrelated_started, unrelated_release))
    try:
        assert started.wait(5)
        assert unrelated_started.wait(5)
        lifetime.close()
        pump()
        assert not lifetime.closed
        with pytest.raises(StorageInUse):
            StorageSession.open(tmp_path)
        release.set()
        lifetime.pool().waitForDone(5000)
        for _ in range(10):
            pump()
        assert lifetime.closed
        assert not unrelated_release.is_set()
    finally:
        release.set()
        unrelated_release.set()
        QThreadPool.globalInstance().waitForDone(5000)


def test_retirement_destroys_owned_roots_before_rebinding(tmp_path, monkeypatch):
    from shiboken6 import isValid
    from frontengine.ui.runtime_lifetime import DefaultSettingsLifetime
    monkeypatch.chdir(tmp_path)
    lifetime = DefaultSettingsLifetime.open()
    label = lifetime.adopt(QLabel('owned'))
    lifetime.close()
    assert not lifetime.closed
    for _ in range(10):
        pump()
    assert not isValid(label)
    assert lifetime.closed


def test_main_queued_builtin_completion_is_rejected_after_close(make_main_window):
    from types import SimpleNamespace
    from PySide6.QtCore import Qt
    from frontengine.ui.dialog.pet_asset_install import CharacterSignals
    from frontengine.ui.runtime_lifetime import CloseDisposition
    window = make_main_window({'language': 'English', 'pet_home_running': False})
    page = window.pet_setting_ui
    calls = []
    page._spawn_layered = lambda *_args: calls.append('spawn')
    page._installing['inkside-pip'] = SimpleNamespace(cancel=Event(), done=False)
    page._waiting = [('inkside-pip', None, {})]           # a card's pet waits for its character
    signal = CharacterSignals()
    signal.finished.connect(page._character_installed, Qt.ConnectionType.QueuedConnection)
    signal.finished.emit('inkside-pip', '')
    assert window.request_shutdown() is CloseDisposition.DRAINING
    for _ in range(30):
        pump()
    assert calls == []
    assert window.lifetime.closed


def test_preparing_callback_replays_once_only_after_cancel(tmp_path, monkeypatch):
    from frontengine.ui.runtime_lifetime import DefaultSettingsLifetime
    monkeypatch.chdir(tmp_path)
    lifetime = DefaultSettingsLifetime.open()
    calls = []
    callback = lifetime.guard(lambda: calls.append('result'))
    lifetime.begin_prepare()
    callback()
    assert calls == []
    lifetime.cancel_prepare()
    assert calls == []
    for _ in range(10):
        pump()
    assert calls == ['result']
    lifetime.begin_prepare()
    callback()
    lifetime.close()
    for _ in range(10):
        pump()
    assert calls == ['result']
    assert lifetime.closed


def test_standalone_text_source_drains_without_settings_binding(tmp_path):
    from frontengine.utils.text_source.local_file_source import LocalFileTextSource, FileTextResult
    from frontengine.user_setting.default_storage import default_storage
    from frontengine.user_setting.storage_session import StorageClosed
    started, release = Event(), Event()
    def read(*args):
        started.set()
        assert release.wait(5)
        return FileTextResult('ready', 'late')
    source = LocalFileTextSource(str(tmp_path / 'feed.txt'), reader=read)
    source.start()
    assert started.wait(5)
    with pytest.raises(StorageClosed):
        default_storage()
    source.stop()
    pump()
    assert not source.lifetime.closed
    release.set()
    source.lifetime.pool().waitForDone(5000)
    for _ in range(10):
        pump()
    assert source.lifetime.closed


def test_scoped_text_source_holds_settings_until_actual_read_finishes(tmp_path, monkeypatch):
    from frontengine.utils.text_source.local_file_source import LocalFileTextSource, FileTextResult
    from frontengine.ui.runtime_lifetime import DefaultSettingsLifetime
    monkeypatch.chdir(tmp_path)
    lifetime = DefaultSettingsLifetime.open()
    started, release = Event(), Event()
    def read(*args):
        started.set()
        assert release.wait(5)
        return FileTextResult('ready', 'late')
    source = LocalFileTextSource('feed.txt', reader=read, lifetime=lifetime)
    source.start()
    assert started.wait(5)
    source.stop()
    lifetime.close()
    pump()
    assert not lifetime.closed
    release.set()
    lifetime.pool().waitForDone(5000)
    for _ in range(10):
        pump()
    assert lifetime.closed


def test_failed_save_replays_queued_builtin_result_once(make_main_window, monkeypatch):
    from types import SimpleNamespace
    from PySide6.QtCore import Qt
    from frontengine.ui.dialog.pet_asset_install import CharacterSignals
    from frontengine.ui.runtime_lifetime import CloseDisposition
    import frontengine.ui.main_ui as main_module
    window = make_main_window({'language': 'English', 'pet_home_running': False})
    page = window.pet_setting_ui
    calls = []
    page._spawn_layered = lambda *_args: calls.append('spawn')
    page._installing['inkside-pip'] = SimpleNamespace(cancel=Event(), done=False)
    page._waiting = [('inkside-pip', None, {})]           # a card's pet waits for its character
    signal = CharacterSignals()
    signal.finished.connect(page._character_installed, Qt.ConnectionType.QueuedConnection)
    original = main_module.write_user_setting
    def fail_after_queued_result():
        signal.finished.emit('inkside-pip', '')
        QCoreApplication.processEvents()
        assert calls == []
        raise OSError('disk unavailable')
    monkeypatch.setattr(main_module, 'write_user_setting', fail_after_queued_result)
    assert window.request_shutdown() is CloseDisposition.REFUSED
    assert window.lifetime.accepting
    assert calls == []
    for _ in range(10):
        pump()
    assert calls == ['spawn']
    monkeypatch.setattr(main_module, 'write_user_setting', original)


def test_partial_constructor_holds_binding_until_job_quiesces(tmp_path, monkeypatch):
    from frontengine.ui.main_ui import FrontEngineMainUI
    from frontengine.ui.runtime_lifetime import DefaultSettingsLifetime, MainRuntimeInUse
    monkeypatch.chdir(tmp_path)
    started, release = Event(), Event()
    retained = []
    class Job(QRunnable):
        def run(self):
            started.set()
            assert release.wait(5)
    def fail(window, *args):
        retained.append(window.lifetime)
        window.lifetime.submit(Job())
        assert started.wait(5)
        raise ValueError('constructor failed')
    monkeypatch.setattr(FrontEngineMainUI, '_initialize', fail)
    with pytest.raises(ValueError, match='constructor failed'):
        FrontEngineMainUI(show_system_tray_ray=False, redirect_output=False)
    pump()
    with pytest.raises(MainRuntimeInUse):
        DefaultSettingsLifetime.open(main=True)
    release.set()
    retained[0].pool().waitForDone(5000)
    for _ in range(10):
        pump()
    assert retained[0].closed


def test_translation_retirement_keeps_other_scope_callbacks():
    from frontengine.utils.work_lifetime import WorkLifetime
    from frontengine.utils.multi_language.retranslate import Retranslator
    from PySide6.QtCore import QObject
    translator = Retranslator()
    old, other = WorkLifetime(), WorkLifetime()
    calls = []
    class Receiver(QObject):
        def __init__(self, lifetime, label):
            super().__init__()
            lifetime.adopt(self)
            self.label = label
        def refresh(self):
            calls.append(self.label)
    first, second = Receiver(old, 'old'), Receiver(other, 'other')
    translator.bind_call(first.refresh)
    translator.bind_call(second.refresh)
    old.begin_prepare()
    translator.apply()
    old.cancel_prepare()
    translator.apply()
    assert calls == ['other', 'old', 'other']
    old.close()
    translator.retire(old)
    translator.apply()
    assert calls == ['other', 'old', 'other', 'other']
    other.close()
    for _ in range(10):
        pump()


def test_f12_native_dispatch_refusal_then_retry_keeps_embedded_app(make_main_window, monkeypatch):
    import importlib
    from types import SimpleNamespace
    import frontengine.ui.main_ui as main_module
    critical_module = importlib.import_module('frontengine.utils.critical_exit.critical_exit')
    window = make_main_window({'language': 'English', 'pet_home_running': False})
    original = main_module.write_user_setting
    saves, finished = [], []
    window.shutdown_finished.connect(lambda: finished.append(True))
    def save():
        saves.append(True)
        if len(saves) == 1:
            raise OSError('first save refused')
        original()
    monkeypatch.setattr(main_module, 'write_user_setting', save)
    keys, waits = iter([True, True, False, True]), iter([False, False, False, False, True])
    monkeypatch.setattr(critical_module, 'check_key_is_press', lambda _key: next(keys))
    listener = critical_module.CriticalExit(on_exit=window._critical_requested.emit)
    listener._stopped = SimpleNamespace(wait=lambda _delay: next(waits))
    listener.run()
    for _ in range(40):
        pump()
    assert len(saves) == 2
    assert finished == [True]
    assert window.lifetime.closed


@pytest.mark.parametrize('module_name,class_name,method_name,widget_name', [
    ('video.video_setting_ui', 'VideoSettingUI', '_create_video_widget', 'VideoWidget'),
    ('gif.gif_setting_ui', 'GIFSettingUI', '_create_gif_widget', 'GifWidget'),
    ('image.image_setting_ui', 'ImageSettingUI', '_create_image_widget', 'ImageWidget'),
    ('particle.particle_setting_ui', 'ParticleSettingUI', '_create_particle_widget', 'ParticleOpenGLWidget'),
    ('web.web_setting_ui', 'WEBSettingUI', '_create_web_widget', 'WebWidget'),
    ('text.text_setting_ui', 'TextSettingUI', '_create_text_widget', 'TextWidget'),
])
def test_page_allocation_rejected_before_widget_creation(module_name, class_name, method_name,
                                                        widget_name, tmp_path, monkeypatch):
    import importlib
    from PySide6.QtWidgets import QWidget
    from frontengine.ui.runtime_lifetime import DefaultSettingsLifetime
    monkeypatch.chdir(tmp_path)
    lifetime = DefaultSettingsLifetime.open()
    module = importlib.import_module('frontengine.ui.page.' + module_name)
    page = getattr(module, class_name)(lifetime=lifetime)
    allocated = []
    class Widget(QWidget):
        def __init__(self, *args, **kwargs):
            super().__init__()
            allocated.append(self)
    monkeypatch.setattr(module, widget_name, Widget)
    action = getattr(page, method_name)
    lifetime.begin_prepare()
    action()
    lifetime.cancel_prepare()
    for _ in range(10):
        pump()
    assert allocated == []
    lifetime.close()
    action()
    assert allocated == []
    for _ in range(10):
        pump()
    assert lifetime.closed
    action()
    assert allocated == []


def test_retiring_video_raw_signal_and_file_drop_do_not_open_or_mutate(tmp_path, monkeypatch):
    from frontengine.ui.runtime_lifetime import DefaultSettingsLifetime
    from frontengine.ui.page.video.video_setting_ui import VideoSettingUI
    monkeypatch.chdir(tmp_path)
    lifetime = DefaultSettingsLifetime.open()
    page = VideoSettingUI(lifetime=lifetime)
    opened = []
    monkeypatch.setattr(page, 'choose_and_copy_file_to_cwd_video_dir_then_play', lambda: opened.append(True))
    lifetime.close()
    page.start_button.click()
    page._on_file_dropped('retired.mp4')
    assert opened == []
    assert page.video_path is None
    for _ in range(10):
        pump()
    assert lifetime.closed


def test_modal_video_choice_cannot_resume_after_owner_retires(lifetime_factory, monkeypatch):
    from frontengine.ui.page.video import video_setting_ui as module
    lifetime = lifetime_factory()
    page = module.VideoSettingUI(lifetime=lifetime)
    writes = []
    def choose(_parent):
        lifetime.close()
        return 'late.mp4'
    monkeypatch.setattr(module, 'choose_video', choose)
    monkeypatch.setattr(module, 'add_recent_file', lambda *args: writes.append(args))
    page.choose_and_copy_file_to_cwd_video_dir_then_play()
    assert page.video_path is None
    assert not page.ready_to_play
    assert writes == []
    assert page.video_widget_list == []


def test_retiring_pet_controls_do_not_create_customization_dialog(lifetime_factory, monkeypatch):
    from PySide6.QtWidgets import QDialog
    from frontengine.ui.page.pet.pet_setting_ui import PetSettingUI
    from frontengine.ui.dialog import pet_customization
    lifetime = lifetime_factory()
    page = PetSettingUI(lifetime=lifetime)
    record = page.profile_controls.profiles.create('Retiring')
    page.profile_controls.refresh(selected=record['id'])
    created = []
    def create(*args, **kwargs):
        dialog = QDialog(page)
        created.append(dialog)
        return dialog
    monkeypatch.setattr(pet_customization, 'PetCustomizationDialog', create)
    lifetime.close()
    page.profile_controls.customize()
    assert created == []


def test_retiring_wardrobe_builtin_completion_does_not_update_ui(lifetime_factory, monkeypatch):
    from frontengine.ui.dialog.pet_wardrobe import PetWardrobeDialog
    lifetime = lifetime_factory()
    profiles = lifetime.storage.profiles()
    record = profiles.create('Retiring')
    dialog = PetWardrobeDialog(profiles, record['id'], lifetime=lifetime)
    updates = []
    monkeypatch.setattr(dialog.status, 'setText', lambda text: updates.append(text))
    monkeypatch.setattr(dialog, '_choose_character', lambda *args: updates.append('choose'))
    lifetime.close()
    dialog._builtin_installed('')
    assert updates == []


def test_retiring_customization_cannot_commit_after_final_save(lifetime_factory, monkeypatch):
    from frontengine.ui.page.pet.pet_setting_ui import PetSettingUI
    lifetime = lifetime_factory()
    page = PetSettingUI(lifetime=lifetime)
    profiles = page.profile_controls.profiles
    record = profiles.create('Retiring')
    page.profile_controls.customize(record['id'])
    dialog = page.profile_controls._dialogs[record['id']]
    writes = []
    monkeypatch.setattr(profiles, 'update', lambda *args, **kwargs: writes.append(args))
    lifetime.close()
    assert dialog.apply_changes() is False
    assert writes == []


def test_home_art_worker_drains_without_blocking_main_shutdown(make_main_window):
    window = make_main_window({'language': 'English', 'pet_home_running': False})
    art = window.pet_home_ui.art
    started, release, finished = Event(), Event(), Event()
    class Job(QRunnable):
        def run(self):
            started.set()
            release.wait(2)
            finished.set()
    art.pool.start(Job())
    assert started.wait(5)
    try:
        window.request_shutdown()
        assert not finished.is_set()
        assert not window.lifetime.closed
    finally:
        release.set()
        for _ in range(20):
            pump()


def test_queued_home_art_result_is_discarded_after_shutdown(make_main_window):
    from frontengine.show.pet_game.resident_art import PICTURE_PREFIX
    window = make_main_window({'language': 'English', 'pet_home_running': False})
    art = window.pet_home_ui.art
    changes = []
    art.changed.connect(lambda: changes.append(True))
    art.prepared.emit('retired', PICTURE_PREFIX + 'retired', (None, None, None))
    window.request_shutdown()
    for _ in range(10):
        pump()
    assert changes == []


@pytest.mark.parametrize('decorator_name', ['owned_action', 'owned_callback'])
def test_owned_methods_keep_qt_signal_argument_adaptation(lifetime_factory, decorator_name):
    from PySide6.QtCore import QObject, Signal
    from frontengine.utils import work_lifetime
    decorate = getattr(work_lifetime, decorator_name)
    calls = []

    class Receiver(QObject):
        changed = Signal(int, str)

        def __init__(self):
            super().__init__()
            self.lifetime = lifetime_factory()

        @decorate
        def no_arguments(self):
            calls.append(('none',))

        @decorate
        def first_argument(self, value):
            calls.append(('first', value))

    receiver = Receiver()
    receiver.changed.connect(receiver.no_arguments)
    receiver.changed.connect(receiver.first_argument)
    receiver.changed.emit(7, 'unused')
    assert calls == [('none',), ('first', 7)]
    with pytest.raises(TypeError):
        receiver.first_argument()
    receiver.lifetime.begin_prepare()
    receiver.changed.emit(8, 'pending')
    assert calls == [('none',), ('first', 7)]
    receiver.lifetime.cancel_prepare()
    pump()
    expected = [('none',), ('first', 7)]
    if decorator_name == 'owned_callback':
        expected += [('none',), ('first', 8)]
    assert calls == expected
    receiver.lifetime.close()
    receiver.changed.emit(9, 'retired')
    assert calls == expected


def test_owned_connection_keeps_qt_signal_argument_adaptation(lifetime_factory):
    from PySide6.QtCore import QObject, Signal
    class Sender(QObject):
        changed = Signal(int)
    lifetime = lifetime_factory()
    sender = Sender()
    calls = []
    lifetime.connect_owned(sender.changed, lambda: calls.append('live'))
    sender.changed.emit(7)
    assert calls == ['live']
    lifetime.close()
    sender.changed.emit(8)
    assert calls == ['live']


@pytest.mark.parametrize('decorator_name', ['owned_action', 'owned_callback'])
def test_owned_methods_keep_variadic_fields_defaults_and_keywords(lifetime_factory, decorator_name):
    from PySide6.QtCore import QObject, Signal
    from frontengine.utils import work_lifetime
    decorate = getattr(work_lifetime, decorator_name)
    calls = []

    class Receiver(QObject):
        changed = Signal(int, str)

        def __init__(self):
            super().__init__()
            self.lifetime = lifetime_factory()

        @decorate
        def collect(self, first=0, *rest, marker='signal'):
            calls.append((first, rest, marker))

    receiver = Receiver()
    receiver.changed.connect(receiver.collect)
    receiver.changed.emit(7, 'kept')
    receiver.collect(marker='direct')
    assert calls == [(7, ('kept',), 'signal'), (0, (), 'direct')]
