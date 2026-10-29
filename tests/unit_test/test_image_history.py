"""Opt-in acquisition, bounded storage, persistent cleanup and explicit image reuse."""
import threading
import time

import pytest
from PySide6.QtCore import QObject, Signal, QEvent, QCoreApplication
from PySide6.QtGui import QImage, QColor
from PySide6.QtWidgets import QApplication, QWidget

from frontengine.utils.image_history import repository as module
from frontengine.utils.image_history.repository import ImageHistoryRepository
from frontengine.utils.image_history.service import ImageHistoryService
from frontengine.ui.dialog.image_history_dialog import ImageHistoryDialog


def image(color='red'):
    result = QImage(32, 24, QImage.Format.Format_RGBA8888)
    result.fill(QColor(color))
    result.setDevicePixelRatio(2)
    return result


def wait(predicate):
    deadline = time.monotonic() + 5
    while not predicate() and time.monotonic() < deadline:
        QApplication.processEvents()
        threading.Event().wait(.005)
    assert predicate()


def test_repository_deduplicates_and_reopens_only_after_persistence_opt_in(tmp_path):
    path = tmp_path/'history.sqlite3'
    repository = ImageHistoryRepository(path)
    try:
        identity = repository.add(image())
        assert repository.add(image()) == identity
        repository.set_pinned(identity, True)
        assert len(repository.entries()) == 1 and repository.entries()[0]['pinned']
        assert repository.image(identity).devicePixelRatio() == 1
        assert not path.exists()
        repository.configure(persistent=True, limit=50, capacity_mib=64)
        assert path.exists()
        repository.close()
        repository = ImageHistoryRepository(path, persistent=True)
        assert repository.entries()[0]['id'] == identity
        repository.configure(persistent=False, limit=50, capacity_mib=64)
        assert not path.exists() and repository.image(identity).pixelColor(0,0) == QColor('red')
    finally:
        repository.close()


def test_pinned_capacity_is_hard_bound_and_failed_insert_rolls_back(tmp_path):
    repository = ImageHistoryRepository(tmp_path/'history.sqlite3', limit=10)
    try:
        for index in range(10):
            identity = repository.add(image(QColor(index,0,0)))
            repository.set_pinned(identity, True)
        before = [entry['id'] for entry in repository.entries()]
        with pytest.raises(ValueError, match='Pinned'):
            repository.add(image('blue'))
        assert [entry['id'] for entry in repository.entries()] == before
        repository.set_pinned(before[-1], False)
        repository.add(image('blue'))
        assert len(repository.entries()) == 10
        repository.clear()
        assert repository.entries() == []
    finally:
        repository.close()


def test_payload_eviction_reserves_space_before_bounded_database_insert(tmp_path):
    import numpy
    repository = ImageHistoryRepository(tmp_path/'history.sqlite3', persistent=True)
    random = numpy.random.default_rng(42)
    repository.capacity = 36 * 1024
    repository.connection.execute('PRAGMA max_page_count=16')
    try:
        for _index in range(8):
            pixels = random.integers(0,256,(64,64,4),dtype=numpy.uint8)
            pixels[:,:,3] = 255
            value = QImage(pixels.data,64,64,256,QImage.Format.Format_RGBA8888).copy()
            repository.add(value)
        assert len(repository.entries()) == 2
        assert repository.path.stat().st_size <= 65536
    finally:
        repository.close()


def test_digest_oversize_and_failed_reconfiguration_are_explicit(tmp_path, monkeypatch):
    repository = ImageHistoryRepository(tmp_path/'history.sqlite3')
    try:
        identity = repository.add(image(), text='Example OCR')
        assert len(repository.entries(text='example')) == 1
        repository.connection.execute('UPDATE images SET png=? WHERE id=?', (b'wrong', identity))
        repository.connection.commit()
        with pytest.raises(ValueError, match='digest'):
            repository.image(identity)
        with pytest.raises(ValueError):
            repository.configure(persistent=True, limit=1, capacity_mib=64)
        assert repository.limit == 50 and not repository.persistent
        monkeypatch.setattr(module, 'MAX_IMAGE_BYTES', 1)
        with pytest.raises(ValueError, match='eight MiB'):
            repository.add(image('blue'))
    finally:
        repository.close()


def test_bad_database_failure_and_opt_out_recovery(tmp_path):
    path = tmp_path/'history.sqlite3'
    path.write_bytes(b'invalid sqlite')
    service = ImageHistoryService(path, {'persistent': True}, clipboard_provider=lambda: None)
    failures, results = [], []
    service.failed.connect(lambda kind, message: failures.append((kind,message)))
    service.result.connect(lambda kind, value: results.append((kind,value)))
    try:
        service.request('list')
        wait(lambda: bool(failures))
        assert failures[0][0] == 'list'
        service.request('configure', enabled=False, persistent=False, limit=50, capacity_mib=64)
        wait(lambda: any(kind=='configure' for kind,_value in results))
        assert not path.exists()
    finally:
        service.stop()
        service.worker.thread.join(5)


class Clipboard(QObject):
    dataChanged = Signal()
    def __init__(self):
        super().__init__()
        self.value, self.reads, self.copied = image(), 0, []
    def image(self):
        self.reads += 1
        return self.value
    def setImage(self, value):
        self.copied.append(value.copy())


def test_no_clipboard_access_before_opt_in_and_stop_disconnects(tmp_path):
    clipboard = Clipboard()
    calls = []
    def provider():
        calls.append(True)
        return clipboard
    service = ImageHistoryService(tmp_path/'history.sqlite3', clipboard_provider=provider)
    results = []
    service.result.connect(lambda kind,value: results.append((kind,value)))
    try:
        assert service.worker is None and calls == []
        clipboard.dataChanged.emit()
        assert clipboard.reads == 0 and not service.capture(image())
        service.request('configure', enabled=True, persistent=False, limit=50, capacity_mib=64)
        wait(lambda: service.config['enabled'])
        clipboard.dataChanged.emit()
        wait(lambda: any(kind=='capture' for kind,_value in results))
        assert clipboard.reads == 1
        service.stop()
        clipboard.dataChanged.emit()
        assert clipboard.reads == 1 and not service.timer.isActive()
        service.worker.thread.join(5)
        assert not service.worker.thread.is_alive() and service.worker.image is None
    finally:
        service.stop()


def test_blocked_compressor_keeps_only_latest_clipboard_image(tmp_path, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    encoded = []
    original = module.encode_image
    def blocked(value):
        encoded.append(value.pixelColor(0,0).name())
        if len(encoded)==1:
            entered.set()
            assert release.wait(5)
        return original(value)
    monkeypatch.setattr(module, 'encode_image', blocked)
    service = ImageHistoryService(tmp_path/'history.sqlite3', {'enabled': True}, clipboard_provider=lambda: None)
    try:
        service.capture(image())
        assert entered.wait(5)
        for index in range(50):
            service.capture(image(QColor(index,0,0)))
        assert service.worker.dropped == 49
        assert service.worker.image.pixelColor(0,0) == QColor(49,0,0)
        release.set()
        wait(lambda: len(encoded)==2)
        assert encoded == ['#ff0000','#310000']
    finally:
        release.set()
        service.stop()
        service.worker.thread.join(5)


def test_dialog_opening_does_not_enable_recording_and_explicit_reuse(tmp_path):
    service = ImageHistoryService(tmp_path/'history.sqlite3', clipboard_provider=lambda: None)
    clipboard = Clipboard()
    owner = QWidget()
    reused = []
    owner.tools_setting_ui = type('Tools', (), {'_pin_edited_capture': lambda self, value: reused.append(('pin', value))})()
    owner.image_setting_ui = type('Images', (), {'add_reference_image': lambda self, value: reused.append(('board',value))})()
    dialog = ImageHistoryDialog(service, owner, clipboard_provider=lambda: clipboard)
    try:
        dialog.show()
        wait(lambda: service.worker is not None)
        assert not service.config['enabled']
        service.request('configure', enabled=True, persistent=False, limit=50, capacity_mib=64)
        wait(lambda: service.config['enabled'])
        service.capture(image())
        wait(lambda: dialog.entries.count()==1)
        dialog.entries.setCurrentRow(0)
        for action in ('copy','pin','board'):
            dialog._get_image(action)
            wait(lambda: not dialog.image_busy)
        assert len(clipboard.copied)==1 and [kind for kind,_value in reused]==['pin','board']
        assert all(value.pixelColor(0,0)==QColor('red') for _kind,value in reused)
        dialog._clear()
        wait(lambda: dialog.entries.count()==0)
        dialog.close()
        assert dialog.entries.count()==0
    finally:
        service.stop()
        service.worker.thread.join(5)
        dialog.close()
        owner.deleteLater()
        QCoreApplication.sendPostedEvents(owner,QEvent.Type.DeferredDelete)


@pytest.mark.parametrize('kind,args', [('pin',{'id':'bad','value':True}),('configure',{'enabled':True}),('list',{'text':123}),('image',{'id':'a'*64,'action':'upload'})])
def test_request_boundary_rejects_bad_data_without_starting_a_worker(tmp_path,kind,args):
    service = ImageHistoryService(tmp_path/'history.sqlite3', clipboard_provider=lambda: None)
    with pytest.raises(ValueError):
        service.request(kind,**args)
    assert service.worker is None
    service.stop()
