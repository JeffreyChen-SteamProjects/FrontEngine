"""Opt-in capture indexing uses injected local OCR and never observes the clipboard."""
from datetime import datetime, timezone
from threading import Event
import time

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtGui import QImage, QColor

from frontengine.ui.dialog.image_history_dialog import ImageHistoryDialog
from frontengine.utils.image_history.capture_service import CaptureHistoryService
from frontengine.utils.image_history.repository import ImageHistoryRepository
from frontengine.utils.screen_text.local_ocr import OcrResult


def image() -> QImage:
    result = QImage(32, 24, QImage.Format.Format_RGBA8888)
    result.fill(QColor('red'))
    return result


def wait(predicate) -> None:
    deadline = time.monotonic() + 5
    while not predicate() and time.monotonic() < deadline:
        QApplication.processEvents()
        Event().wait(.005)
    assert predicate()


def cleanup(service) -> None:
    service.stop()
    if service.worker is not None:
        service.worker.thread.join(5)
        assert not service.worker.thread.is_alive()


def test_capture_opt_in_local_index_search_delete_and_persistent_reopen(tmp_path):
    calls, results = [], []
    def recognize(data):
        calls.append(data)
        return OcrResult('success', 'Receipt ALPHA 123', 'injected local')
    path = tmp_path/'capture.sqlite3'
    service = CaptureHistoryService(path, indexer=recognize)
    service.result.connect(lambda kind, value: results.append((kind, value)))
    try:
        assert service.worker is None and not service.capture(image()) and not calls
        service.request('configure', enabled=True, persistent=True, limit=50, capacity_mib=64)
        wait(lambda: service.config['enabled'])
        assert service.clipboard is None and service.capture(image())
        wait(lambda: any(kind == 'capture' for kind, _ in results))
        assert len(calls) == 1 and calls[0].startswith(b'\x89PNG')
        service.request('list', text='alpha', date=datetime.now().astimezone().date().isoformat())
        wait(lambda: any(kind == 'list' for kind, _ in results))
        entries = next(value for kind, value in results if kind == 'list')
        assert len(entries) == 1 and entries[0]['text'] == 'Receipt ALPHA 123'
    finally:
        cleanup(service)
    repository = ImageHistoryRepository(path, persistent=True)
    try:
        assert len(repository.entries(text='receipt')) == 1
        repository.remove(entries[0]['id'])
        assert repository.entries(text='receipt') == []
        assert repository.connection.execute('SELECT count(*) FROM images').fetchone()[0] == 0
    finally:
        repository.close()


def test_local_failure_keeps_capture_without_cloud_fallback(tmp_path):
    results = []
    def unavailable(_data):
        return OcrResult('unavailable', backend='local', error='No local OCR installed')
    service = CaptureHistoryService(tmp_path/'history.sqlite3', {'enabled': True}, indexer=unavailable)
    service.result.connect(lambda kind, value: results.append((kind, value)))
    try:
        service.capture(image())
        wait(lambda: bool(results))
        kind, result = results[0]
        assert kind == 'capture' and not result['indexed'] and result['error'] == 'No local OCR installed'
        service.request('list')
        wait(lambda: any(kind == 'list' for kind, _ in results))
        entries = next(value for kind, value in results if kind == 'list')
        assert len(entries) == 1 and entries[0]['text'] == ''
    finally:
        cleanup(service)


def test_close_during_local_ocr_drops_pending_inputs_and_results(tmp_path):
    entered, release = Event(), Event()
    calls, results = [], []
    def blocked(_data):
        calls.append(True)
        entered.set()
        assert release.wait(5)
        return OcrResult('success', 'late', 'local')
    service = CaptureHistoryService(tmp_path/'history.sqlite3', {'enabled': True}, indexer=blocked)
    service.result.connect(lambda *args: results.append(args))
    try:
        service.capture(image())
        assert entered.wait(5)
        for _ in range(20):
            service.capture(image())
        assert service.worker.dropped == 19
        service.stop()
        release.set()
        cleanup(service)
        assert len(calls) == 1 and not results and service.worker.take_results() == []
    finally:
        release.set()
        cleanup(service)


def test_date_search_uses_user_local_day_instead_of_stored_utc_prefix(tmp_path):
    repository = ImageHistoryRepository(tmp_path/'history.sqlite3')
    try:
        at = '2026-10-08T23:59:59-12:00'
        local_day = datetime.fromisoformat(at).astimezone().date().isoformat()
        repository.add(image(), text='local midnight', at=at)
        assert len(repository.entries(date=local_day)) == 1
        assert repository.entries(date='2000-01-01') == []
        assert datetime.fromisoformat(at).astimezone(timezone.utc).date().isoformat() == '2026-10-09'
    finally:
        repository.close()


def test_capture_dialog_search_and_repin_are_explicit(tmp_path):
    service = CaptureHistoryService(tmp_path/'history.sqlite3', indexer=lambda _: OcrResult('success', 'BETA', 'local'))
    owner, reused = QWidget(), []
    owner.tools_setting_ui = type('Tools', (), {'_pin_edited_capture': lambda self, value: reused.append(value)})()
    dialog = ImageHistoryDialog(service, owner, capture_mode=True, clipboard_provider=lambda: None)
    try:
        dialog.show()
        assert not service.config['enabled']
        dialog.enabled.setChecked(True)
        dialog._configure()
        wait(lambda: service.config['enabled'])
        service.capture(image())
        wait(lambda: dialog.entries.count() == 1)
        dialog.search.setText('missing')
        wait(lambda: dialog.entries.count() == 0)
        dialog.search.setText('beta')
        wait(lambda: dialog.entries.count() == 1)
        assert not reused
        dialog.entries.setCurrentRow(0)
        dialog._get_image('pin')
        wait(lambda: bool(reused))
        assert len(reused) == 1
        dialog._remove()
        wait(lambda: dialog.entries.count() == 0)
    finally:
        cleanup(service)
        dialog.close()
        owner.deleteLater()
        QCoreApplication.sendPostedEvents(owner, QEvent.Type.DeferredDelete)
