"""Local task durability, timezone semantics, idempotent import and UI ownership."""
from datetime import date
import json
from threading import Event
import time

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtWidgets import QApplication, QWidget

from frontengine.utils.todo.calendar_import import parse_calendar, parse_time
from frontengine.utils.todo.repository import TodoRepository, today_items, validate_items
from frontengine.utils.todo.service import TodoService
from frontengine.ui.dialog.todo_dialog import TodoDialog
from frontengine.show.notes.todo_widget import TodoWidget


def calendar(body: str, kind: str = 'VEVENT') -> bytes:
    return f'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:{kind}\r\n{body}\r\nEND:{kind}\r\nEND:VCALENDAR\r\n'.encode()


def wait(predicate) -> None:
    deadline = time.monotonic() + 5
    while not predicate() and time.monotonic() < deadline:
        QApplication.processEvents()
        Event().wait(.005)
    assert predicate()


def test_folded_escaped_text_all_day_and_exclusive_end():
    entries = parse_calendar(calendar('UID:day-1\r\nSUMMARY:Long\\, title\r\n continued\r\n'
                                      'DESCRIPTION:one\\ntwo\\;three\\\\four\r\n'
                                      'DTSTART;VALUE=DATE:20261008\r\nDTEND;VALUE=DATE:20261010'))
    assert entries[0]['title'] == 'Long, titlecontinued'
    assert entries[0]['description'] == 'one\ntwo;three\\four'
    assert today_items(entries, date(2026, 10, 8)) == entries
    assert today_items(entries, date(2026, 10, 9)) == entries
    assert today_items(entries, date(2026, 10, 10)) == []


def test_iana_zone_utc_floating_and_dst_pre_transition_resolution():
    assert parse_time('20261008T090000', {'TZID': 'Asia/Taipei'})['value'] == '2026-10-08T01:00:00+00:00'
    assert parse_time('20260308T023000', {'TZID': 'America/New_York'})['value'] == '2026-03-08T07:30:00+00:00'
    assert parse_time('20261101T013000', {'TZID': 'America/New_York'})['value'] == '2026-11-01T05:30:00+00:00'
    assert parse_time('20261008T090000', {}) == {'kind': 'floating', 'value': '2026-10-08T09:00:00'}
    assert parse_time('20261008T090000Z', {})['kind'] == 'utc'
    with pytest.raises(ValueError, match='Unknown'):
        parse_time('20261008T090000', {'TZID': 'Not/ARealZone'})


def test_duration_observes_nominal_days_across_dst_and_midnight_end_exclusion():
    entry = parse_calendar(calendar('UID:duration\r\nSUMMARY:weekend\r\n'
                                    'DTSTART;TZID=America/New_York:20260307T120000\r\nDURATION:P1D'))[0]
    assert entry['start']['value'] == '2026-03-07T17:00:00+00:00'
    assert entry['due']['value'] == '2026-03-08T16:00:00+00:00'
    entry = parse_calendar(calendar('UID:midnight\r\nSUMMARY:night\r\n'
                                    'DTSTART:20261008T230000\r\nDTEND:20261009T000000'))[0]
    assert today_items([entry], date(2026, 10, 8)) == [entry]
    assert today_items([entry], date(2026, 10, 9)) == []


def test_uid_sequence_done_preservation_recurring_instance_and_cancel(tmp_path):
    repository = TodoRepository(tmp_path/'tasks.json')
    data = calendar('UID:meeting\r\nSUMMARY:original\r\nDTSTART:20261008T090000Z\r\nSEQUENCE:2')
    items = repository.apply('import', {'data': data})
    identity = items[0]['id']
    repository.apply('done', {'id': identity, 'value': True})
    assert len(repository.apply('import', {'data': data})) == 1
    assert repository.items[identity]['done']
    repository.apply('import', {'data': data.replace(b'original', b'updated').replace(b'SEQUENCE:2', b'SEQUENCE:3')})
    repository.apply('import', {'data': data})
    assert repository.items[identity]['title'] == 'updated'
    instance = data.replace(b'SUMMARY:original', b'RECURRENCE-ID:20261008T090000Z\r\nSUMMARY:instance')
    assert len(repository.apply('import', {'data': instance})) == 2
    cancelled = calendar('UID:meeting\r\nSTATUS:CANCELLED\r\nSEQUENCE:4')
    assert len(repository.apply('import', {'data': cancelled})) == 1
    assert identity not in [item['id'] for item in TodoRepository(repository.path).snapshot()]
    assert len(repository.apply('import', {'data': data})) == 1
    assert repository.apply('clear', {}) == []
    assert TodoRepository(repository.path).items == {}


def test_utf8_fold_can_split_a_multibyte_character_and_duplicate_attendees_are_ignored():
    data = calendar('UID:unicode\r\nSUMMARY:界\r\nDTSTART:20261008T090000Z\r\n'
                    'ATTENDEE:mailto:one@example.invalid\r\nATTENDEE:mailto:two@example.invalid')
    data = data.replace('界'.encode(), b'\xe7\r\n \x95\x8c')
    assert parse_calendar(data)[0]['title'] == '界'


def test_task_due_overdue_undated_completion_and_cross_session(tmp_path):
    repository = TodoRepository(tmp_path/'tasks.json')
    for title, due in [('undated', None), ('overdue', {'kind': 'date', 'value': '2026-10-07'}),
                       ('future', {'kind': 'date', 'value': '2026-10-09'})]:
        repository.apply('add', {'title': title, 'due': due})
    reloaded = TodoRepository(repository.path)
    assert [item['title'] for item in today_items(reloaded.snapshot(), date(2026, 10, 8))] == ['undated', 'overdue']
    identity = next(item['id'] for item in reloaded.snapshot() if item['title'] == 'overdue')
    reloaded.apply('done', {'id': identity, 'value': True})
    assert [item['title'] for item in today_items(TodoRepository(repository.path).snapshot(), date(2026, 10, 8))] == ['undated']


@pytest.mark.parametrize('extra', ['RRULE:FREQ=DAILY', 'RDATE:20261009T090000Z',
                                 'DTEND:20261007T090000Z', 'DTSTART:20261008T090000Z'])
def test_invalid_or_unsupported_import_is_atomic(tmp_path, extra):
    repository = TodoRepository(tmp_path/'tasks.json')
    repository.apply('add', {'title': 'keep', 'due': None})
    before = repository.path.read_bytes()
    with pytest.raises(ValueError):
        repository.apply('import', {'data': calendar('UID:invalid\r\nSUMMARY:test\r\nDTSTART:20261008T090000Z\r\n' + extra)})
    assert repository.path.read_bytes() == before and repository.snapshot()[0]['title'] == 'keep'


def test_failed_write_and_malformed_document_preserve_existing_state(tmp_path):
    repository = TodoRepository(tmp_path/'tasks.json')
    repository.apply('add', {'title': 'safe', 'due': None})
    original = repository.path.read_bytes()
    def failed(_path, _data):
        raise OSError('injected disk failure')
    repository.writer = failed
    with pytest.raises(OSError):
        repository.apply('add', {'title': 'lost', 'due': None})
    assert repository.path.read_bytes() == original and len(repository.items) == 1
    malformed = json.loads(original)
    malformed['items'][0]['due'] = {'kind': 'utc', 'value': '2026-10-08T10:00:00'}
    with pytest.raises(ValueError, match='timezone'):
        validate_items(malformed['items'])
    repository.path.write_text('{broken', encoding='utf-8')
    with pytest.raises(ValueError):
        TodoRepository(repository.path)


def test_service_serializes_and_close_drops_late_results(tmp_path):
    entered, release = Event(), Event()
    from frontengine.utils.todo.repository import atomic_write
    def blocked(path, data):
        entered.set()
        assert release.wait(5)
        atomic_write(path, data)
    service = TodoService(tmp_path/'tasks.json', writer=blocked)
    results = []
    service.result.connect(lambda *args: results.append(args))
    try:
        assert service.thread is None and not service.timer.isActive()
        assert service.request('add', title='one', due=None)
        assert entered.wait(5)
        assert not service.request('add', title='two', due=None)
        service.stop()
        release.set()
        service.thread.join(5)
        assert not results and service.mailbox is None and not service.timer.isActive()
        assert len(TodoRepository(service.path).items) == 1
    finally:
        release.set()
        service.stop()
        if service.thread:
            service.thread.join(5)


def test_editor_and_today_overlay_share_persistent_checklist_and_stop_timers(tmp_path):
    service = TodoService(tmp_path/'tasks.json')
    owner = QWidget()
    dialog = TodoDialog(service, owner)
    from frontengine.ui.dialog.todo_dialog import TodoPanel
    widget = TodoWidget(lambda parent: TodoPanel(service, parent, editor=False))
    try:
        dialog.show()
        widget.show()
        widget.set_render_backend('gpu')
        assert widget._compositor is None and widget.render_backend == 'software'
        wait(lambda: service.loaded)
        dialog.panel.title.setText('native-free task')
        dialog.panel.has_due.setChecked(True)
        dialog.panel._add()
        wait(lambda: not service.busy)
        assert len(service.items) == 1 and service.items[0]['due']['kind'] == 'utc'
        assert dialog.panel.entries.count() == widget.panel.entries.count() == 1
        widget.panel.entries.item(0).setCheckState(Qt.CheckState.Checked)
        wait(lambda: not service.busy)
        assert widget.panel.entries.count() == 0
        assert dialog.panel.entries.item(0).checkState() == Qt.CheckState.Checked
        widget.hide()
        assert not widget.panel.timer.isActive()
        widget.show()
        assert widget.panel.timer.isActive()
        widget.close()
        assert widget.closed and not widget.panel.timer.isActive()
    finally:
        service.stop()
        if service.thread:
            service.thread.join(5)
        if not widget.closed:
            widget.close()
        dialog.close()
        owner.deleteLater()
        QCoreApplication.sendPostedEvents(owner, QEvent.Type.DeferredDelete)
        QCoreApplication.sendPostedEvents(widget, QEvent.Type.DeferredDelete)
