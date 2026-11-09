"""
測試共用設定：強制 Qt 使用 offscreen 平台，並把工作目錄移到暫存區，
避免匯入 frontengine 時產生的日誌檔落在專案目錄。

Shared test setup: force Qt's offscreen platform and run from a temporary
working directory so the log file created on import does not land in the repo.
"""
import os
import tempfile
import sys
import gc

import pytest

# 必須在匯入任何 Qt 模組前設定 / Must be set before any Qt module is imported.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def _isolated_macos_frameworks(monkeypatch):
    """Unit tests never start native host capture/audio or request TCC permission."""
    if sys.platform != 'darwin':
        return
    from frontengine.utils.macos import backend

    def unavailable(name):
        raise ImportError('Native framework is isolated in unit tests: ' + name)

    monkeypatch.setattr(backend, '_backend', backend.MacOSBackend(loader=unavailable))


@pytest.fixture(autouse=True)
def _never_read_the_real_session_lock(monkeypatch):
    """A headless runner has no input desktop and would read as locked, pausing every home."""
    from frontengine.utils.session_lock import session_lock
    monkeypatch.setattr(session_lock, "is_session_locked", lambda: False)


@pytest.fixture(autouse=True)
def _never_read_the_real_workshop_folder(monkeypatch):
    """The pet home would load packs subscribed on this machine's Steam; tests use their own."""
    from frontengine.ui.page.pet_game import home_page
    monkeypatch.setattr(home_page, "workshop_pack_roots", lambda: [])


@pytest.fixture(scope="session", autouse=True)
def _run_from_temporary_directory():
    """整個測試 session 在暫存目錄下執行 / Run the session from a temp directory."""
    original = os.getcwd()
    with tempfile.TemporaryDirectory() as directory:
        os.chdir(directory)
        try:
            yield directory
        finally:
            os.chdir(original)


@pytest.fixture(scope="session", autouse=True)
def _qt_application():
    """
    整個 session 共用一個 QApplication。QPixmap、QMovie 這類類別在沒有
    QGuiApplication 時會直接讓行程中止（不是丟例外），所以這裡一定要先建好。
    One QApplication for the whole session. Classes like QPixmap and QMovie
    abort the process - they do not raise - when no QGuiApplication exists, so
    it has to be in place before any test touches them.
    """
    from PySide6.QtWidgets import QApplication

    application = QApplication.instance() or QApplication([])
    yield application
    _release_leftovers(application)


@pytest.fixture
def make_main_window(tmp_path, monkeypatch):
    """
    Build FrontEngineMainUI with real owned persistence in its own folder.
    Every window built is closed and the working directory restored at teardown.
    """
    import json
    from frontengine.ui.main_ui import FrontEngineMainUI
    original = os.getcwd()
    windows = []

    def build(settings=None):
        for previous in windows:
            if not previous.lifetime.closed:
                previous.close()
                _drain_lifetimes([previous.lifetime])
        (tmp_path / "user_setting.json").write_text(json.dumps(settings or {"language": "English"}),
                                                    encoding="utf-8")
        os.chdir(tmp_path)
        window = FrontEngineMainUI(show_system_tray_ray=False, redirect_output=False)
        windows.append(window)
        return window

    try:
        yield build
    finally:
        from PySide6.QtCore import QCoreApplication, QEvent
        monkeypatch.undo()
        for window in windows:
            window.close()
            _drain_lifetimes([window.lifetime])
            window.deleteLater()            # closing only hides it: thousands of widgets stayed alive
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        os.chdir(original)


def _release_leftovers(application) -> None:
    """Stop listener threads and delete leftover top-level widgets while Python is still whole.

    Tests leave thousands of top-level widgets and one emergency-exit listener per
    main window. Left to interpreter shutdown, they were torn down in arbitrary order
    and the Windows CI job sometimes exited 1 after every test had passed.
    """
    import threading
    from PySide6.QtCore import QCoreApplication, QEvent
    from frontengine.utils.critical_exit.critical_exit import CriticalExit
    for thread in threading.enumerate():
        if isinstance(thread, CriticalExit):
            thread.stop()
    for widget in application.topLevelWidgets():
        widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    application.processEvents()
    gc.collect()


def _flush_deleted_widgets() -> None:
    """Run the pending deleteLater() calls, then collect cycles, on the GUI thread.

    Tests rarely run an event loop at the level deleteLater() was called from, so without
    this the widgets they gave up stayed alive for the rest of the session - 77,000 of them
    by the late modules, slowing every later test and starving timer-driven ones.
    """
    from PySide6.QtCore import QCoreApplication, QEvent
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    gc.collect()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.fixture(autouse=True)
def _delete_closed_test_windows(_qt_application):
    """Delete the top-level windows a test built and closed, once its fixtures are torn down.

    Closing only hides a window without WA_DeleteOnClose: every desktop pet test left about
    232 widgets per pet (menus, speech bubbles, the settings page around it) and the
    screensaver tests about 4,800, all alive until the session ended. Windows that already
    existed (module fixtures) and windows still shown are left alone.
    """
    from PySide6.QtWidgets import QApplication
    from shiboken6 import getCppPointer
    before = {getCppPointer(widget)[0] for widget in QApplication.topLevelWidgets()}
    yield
    from PySide6.QtCore import QCoreApplication, QEvent
    for widget in QApplication.topLevelWidgets():
        if getCppPointer(widget)[0] not in before and not widget.isVisible():
            widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.fixture(autouse=True, scope="module")
def _release_test_widget_cycles(_qt_application):
    """Release cyclic and deleted test widgets on their GUI thread before another module starts."""
    _flush_deleted_widgets()
    yield
    _flush_deleted_widgets()


def _drain_lifetimes(lifetimes):
    from time import monotonic
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtTest import QTest
    deadline = monotonic() + 120
    while any(not lifetime.closed for lifetime in lifetimes) and monotonic() < deadline:
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        QCoreApplication.processEvents()
        QTest.qWait(10)
    unfinished = [(lifetime.state, lifetime.error) for lifetime in lifetimes if not lifetime.closed]
    assert not unfinished, f'Owned runtimes did not retire: {unfinished}'


@pytest.fixture
def lifetime_factory(tmp_path, monkeypatch, _run_from_temporary_directory):
    from pathlib import Path
    from frontengine.ui.runtime_lifetime import DefaultSettingsLifetime
    lifetimes = {}
    def create():
        if Path.cwd().resolve() == Path(_run_from_temporary_directory).resolve():
            monkeypatch.chdir(tmp_path)
        root = Path.cwd().resolve()
        if root not in lifetimes or lifetimes[root].closed:
            lifetimes[root] = DefaultSettingsLifetime.open()
        return lifetimes[root]
    yield create
    monkeypatch.undo()
    for lifetime in lifetimes.values():
        lifetime.close()
    _drain_lifetimes(list(lifetimes.values()))


@pytest.fixture
def storage_factory(tmp_path):
    from pathlib import Path
    from frontengine.user_setting.storage_session import StorageClosed, StorageSession
    from frontengine.user_setting.default_storage import default_storage
    owners = {}
    def create(path=None):
        root = Path(path or tmp_path).resolve()
        try:
            default = default_storage()
        except StorageClosed:
            default = None
        if default is not None and default.directory == root:
            return default
        if root not in owners:
            owners[root] = StorageSession.open(root)
        return owners[root]
    yield create
    for owner in reversed(tuple(owners.values())):
        owner.close()


@pytest.fixture
def home_store_factory(storage_factory, lifetime_factory):
    from frontengine.user_setting.pet_game_save import HomeSaveStore
    stores = []
    def create(path, catalog, mode='manage', **kwargs):
        store = HomeSaveStore(storage_factory(path), catalog, mode, **kwargs)
        stores.append(store)
        return store
    yield create
    for store in reversed(stores):
        store.close()


@pytest.fixture(scope="session")
def _builtin_pet_assets(tmp_path_factory):
    """One built-in character, installed once per run: building it takes seconds."""
    from frontengine.show.pet.asset_library import PetAssetLibrary
    from frontengine.show.pet.inkside.library import install_builtin
    root = tmp_path_factory.mktemp("builtin-pet-assets").resolve() / "pet-assets"
    install_builtin(PetAssetLibrary(root), "inkside-mochi", wardrobe=False)
    return root


@pytest.fixture
def layered_pets(_builtin_pet_assets, monkeypatch):
    """Ready a pet page to spawn layered pets at once: the built-in is in its library and chosen.

    Pets are layered only, so a page spawns a pet wearing a character; without this it would
    install one in the background first. Only the character is installed (its clothes take most of
    a minute), so a wardrobe opened here does not start adding the missing built-in clothes.
    """
    import shutil
    from frontengine.ui.dialog.pet_wardrobe import PetWardrobeDialog
    monkeypatch.setattr(PetWardrobeDialog, "missing_builtin_clothes", lambda self: None)

    def ready(page, character="inkside-mochi"):
        target = page.lifetime.storage.directory / "pet-assets"
        shutil.copytree(_builtin_pet_assets, target, dirs_exist_ok=True)
        page._choose_character(character)
        return page
    return ready
