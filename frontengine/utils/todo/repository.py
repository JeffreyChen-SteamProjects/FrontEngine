"""Atomic validated local task persistence and UID-based calendar merging."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
from typing import Callable
from uuid import uuid4

from PySide6.QtCore import QSaveFile, QIODevice

from frontengine.utils.todo.calendar_import import parse_calendar, local_day

MAX_DOCUMENT_BYTES = 4 * 1024 * 1024


def validate_moment(value) -> dict | None:
    """Reject invalid stored dates rather than silently shifting or discarding them."""
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {'kind', 'value'} or not isinstance(value['value'], str):
        raise ValueError('Invalid task date')
    if value['kind'] == 'date':
        normalized = date.fromisoformat(value['value']).isoformat()
    elif value['kind'] in ('utc', 'floating'):
        parsed = datetime.fromisoformat(value['value'])
        if (parsed.tzinfo is not None) != (value['kind'] == 'utc'):
            raise ValueError('Task timezone does not match its date type')
        normalized = parsed.astimezone(timezone.utc).isoformat() if value['kind'] == 'utc' else parsed.isoformat()
    else:
        raise ValueError('Unknown task date type')
    return {'kind': value['kind'], 'value': normalized}


def validate_items(items) -> dict:
    """Accept at most 500 bounded, uniquely identified records of the version-one schema."""
    if not isinstance(items, list) or len(items) > 500:
        raise ValueError('Task document supports at most 500 items')
    result = {}
    for item in items:
        fields = {'id', 'title', 'description', 'kind', 'start', 'due', 'done', 'sequence', 'cancelled'}
        if not isinstance(item, dict) or set(item) != fields:
            raise ValueError('Invalid task record fields')
        identity = item['id']
        if not isinstance(identity, str) or not re.fullmatch('[0-9a-f]{32}|[0-9a-f]{64}', identity) or identity in result:
            raise ValueError('Invalid or duplicate task identifier')
        if not isinstance(item['title'], str) or not item['title'].strip() or len(item['title']) > 1000:
            raise ValueError('Task title must contain 1–1000 characters')
        if not isinstance(item['description'], str) or len(item['description']) > 2000:
            raise ValueError('Task description exceeds 2000 characters')
        if item['kind'] not in ('event', 'task') or type(item['done']) is not bool or type(item['cancelled']) is not bool:
            raise ValueError('Invalid task type/completion')
        if type(item['sequence']) is not int or not 0 <= item['sequence'] <= 999999999:
            raise ValueError('Invalid task calendar sequence')
        start, due = validate_moment(item['start']), validate_moment(item['due'])
        if item['kind'] == 'event' and start is None and not item['cancelled']:
            raise ValueError('Event requires a start time')
        if start is not None and due is not None and (start['kind'] != due['kind'] or start['value'] >= due['value']):
            raise ValueError('Event/task end must follow its start')
        result[identity] = dict(item, start=start, due=due)
    return result


def atomic_write(path: Path, data: bytes) -> None:
    """Commit a complete document without exposing a truncated previous file."""
    if path.is_symlink():
        raise ValueError('Task database cannot be a symlink')
    target = QSaveFile(str(path))
    if not target.open(QIODevice.OpenModeFlag.WriteOnly):
        raise OSError(target.errorString())
    if target.write(data) != len(data):
        target.cancelWriting()
        raise OSError('Task document write was incomplete')
    if not target.commit():
        raise OSError(target.errorString())


class TodoRepository:
    """One-worker owner; apply changes only after their atomic write succeeds."""

    def __init__(self, path: str | Path, *, writer: Callable = atomic_write) -> None:
        self.path, self.writer = Path(path), writer
        self.items = {}
        if self.path.is_symlink():
            raise ValueError('Task database cannot be a symlink')
        if self.path.exists():
            with self.path.open('rb') as stream:
                data = stream.read(MAX_DOCUMENT_BYTES + 1)
            if len(data) > MAX_DOCUMENT_BYTES:
                raise ValueError('Task document exceeds four MiB')
            document = json.loads(data)
            if not isinstance(document, dict) or set(document) != {'version', 'items'} or type(document['version']) is not int or document['version'] != 1:
                raise ValueError('Unsupported task document version')
            self.items = validate_items(document['items'])

    def snapshot(self) -> list[dict]:
        """Return detached records so callers cannot mutate durable state accidentally."""
        return deepcopy([item for item in self.items.values() if not item['cancelled']])

    def apply(self, action: str, arguments: dict) -> list[dict]:
        """Validate and persist an add/check/remove/import transaction before publishing state."""
        updated = deepcopy(self.items)
        if action == 'add':
            item = dict(id=uuid4().hex, title=arguments['title'], description='', kind='task', start=None,
                        due=validate_moment(arguments.get('due')), done=False, sequence=0, cancelled=False)
            updated[item['id']] = item
        elif action == 'done':
            if type(arguments['value']) is not bool:
                raise ValueError('Task completion must be a boolean')
            updated[arguments['id']]['done'] = arguments['value']
        elif action == 'remove':
            updated.pop(arguments['id'], None)
        elif action == 'import':
            self._merge(updated, parse_calendar(arguments['data']))
        elif action == 'clear':
            updated.clear()
        else:
            raise ValueError('Unknown task operation')
        normalized = validate_items(list(updated.values()))
        data = json.dumps({'version': 1, 'items': list(normalized.values())}, ensure_ascii=False).encode('utf-8')
        if len(data) > MAX_DOCUMENT_BYTES:
            raise ValueError('Task document exceeds four MiB')
        self.writer(self.path, data)
        self.items = normalized
        return self.snapshot()

    @staticmethod
    def _merge(updated: dict, imported: list[dict]) -> None:
        for item in imported:
            previous = updated.get(item['id'])
            if previous is not None and (item['sequence'] < previous['sequence'] or
                                         (previous['cancelled'] and item['sequence'] == previous['sequence'])):
                continue
            if item['cancelled']:
                tombstone = dict(previous or item, cancelled=True, sequence=item['sequence'])
                updated[item['id']] = tombstone
            else:
                item['done'] = item['done'] or bool(previous and previous['done'])
                updated[item['id']] = item


def today_items(items: list[dict], today: date | None = None) -> list[dict]:
    """Show undated/due/overdue tasks and events overlapping the local calendar day."""
    today = today or date.today()
    result = []
    for item in items:
        if item['done']:
            continue
        start, due = local_day(item['start']), local_day(item['due'])
        if item['kind'] == 'task':
            visible = due is None or due <= today
        elif due is None:
            visible = start == today
        elif item['due']['kind'] == 'date':
            visible = start <= today < due
        else:
            end = datetime.fromisoformat(item['due']['value'])
            if item['due']['kind'] == 'utc':
                end = end.astimezone()
            exclusive_midnight = end.hour == end.minute == end.second == end.microsecond == 0
            visible = start <= today and (today < due if exclusive_midnight else today <= due)
        if visible:
            result.append(deepcopy(item))
    return sorted(result, key=lambda item: (display_sort(item), item['title'].casefold(), item['id']))


def display_sort(item: dict) -> str:
    """Order by local calendar day while keeping undated tasks first."""
    day = local_day(item['start'] if item['kind'] == 'event' else item['due'])
    return day.isoformat() if day else ''
