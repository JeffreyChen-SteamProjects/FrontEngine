"""
測試共用設定：強制 Qt 使用 offscreen 平台，並把工作目錄移到暫存區，
避免匯入 frontengine 時產生的日誌檔落在專案目錄。

Shared test setup: force Qt's offscreen platform and run from a temporary
working directory so the log file created on import does not land in the repo.
"""
import os
import tempfile

import pytest

# 必須在匯入任何 Qt 模組前設定 / Must be set before any Qt module is imported.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


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
