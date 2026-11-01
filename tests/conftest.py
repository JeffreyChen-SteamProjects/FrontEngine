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
    Build FrontEngineMainUI from a settings dict, in its own folder, never writing settings.
    Every window built is closed and the working directory restored at teardown.
    """
    import json
    from frontengine.ui.main_ui import FrontEngineMainUI
    import frontengine.ui.main_ui as main_module
    import frontengine.ui.menu.settings_menu as menu_module

    monkeypatch.setattr(main_module, "write_user_setting", lambda: None)
    monkeypatch.setattr(menu_module, "write_user_setting", lambda: None)
    original = os.getcwd()
    windows = []

    def build(settings=None):
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
        for window in windows:
            window.close()
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


@pytest.fixture(autouse=True, scope="module")
def _release_test_widget_cycles(_qt_application):
    """Release cyclic and deleted test widgets on their GUI thread before another module starts."""
    _flush_deleted_widgets()
    yield
    _flush_deleted_widgets()
