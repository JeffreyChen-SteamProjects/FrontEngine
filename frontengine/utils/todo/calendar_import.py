"""A bounded, explicit subset of RFC 5545; unsupported recurrence is rejected."""
from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
import hashlib
import re

from PySide6.QtCore import QDate, QTime, QDateTime, QTimeZone

MAX_CALENDAR_BYTES = 4 * 1024 * 1024


def unescape(value: str) -> str:
    """Decode iCalendar TEXT escapes without interpreting HTML or URLs."""
    return re.sub(r'\\([nN,;\\])', lambda match: '\n' if match[1].lower() == 'n' else match[1], value)


def parse_time(value: str, parameters: dict) -> dict:
    """Preserve date/floating types, resolve known TZID to UTC with pre-transition offset."""
    if parameters.get('VALUE') == 'DATE':
        if parameters.get('TZID') or not re.fullmatch(r'\d{8}', value):
            raise ValueError('Invalid all-day calendar date')
        return {'kind': 'date', 'value': datetime.strptime(value, '%Y%m%d').date().isoformat()}
    if parameters.get('VALUE', 'DATE-TIME') != 'DATE-TIME' or not re.fullmatch(r'\d{8}T\d{6}Z?', value):
        raise ValueError('Unsupported calendar date/time format')
    adjusted = value[:13] + '59' + value[15:] if value[13:15] == '60' else value
    moment = datetime.strptime(adjusted.rstrip('Z'), '%Y%m%dT%H%M%S')
    if value.endswith('Z'):
        if parameters.get('TZID'):
            raise ValueError('UTC time cannot include TZID')
        return {'kind': 'utc', 'value': moment.replace(tzinfo=timezone.utc).isoformat()}
    if not parameters.get('TZID'):
        return {'kind': 'floating', 'value': moment.isoformat()}
    zone = QTimeZone(parameters['TZID'].encode('utf-8'))
    if not zone.isValid():
        raise ValueError('Unknown calendar timezone: ' + parameters['TZID'])
    qt = QDateTime(QDate(moment.year, moment.month, moment.day), QTime(moment.hour, moment.minute, moment.second),
                   zone, QDateTime.TransitionResolution.RelativeToBefore)
    if not qt.isValid():
        raise ValueError('Calendar date/time cannot be resolved')
    utc = datetime.fromtimestamp(qt.toSecsSinceEpoch(), timezone.utc)
    return {'kind': 'utc', 'value': utc.isoformat()}


def local_day(moment: dict | None) -> date | None:
    """Calendar dates stay calendar dates; instants display in the current local timezone."""
    if moment is None:
        return None
    if moment['kind'] == 'date':
        return date.fromisoformat(moment['value'])
    value = datetime.fromisoformat(moment['value'])
    return value.astimezone().date() if moment['kind'] == 'utc' else value.date()


def display_time(moment: dict | None) -> str:
    """Return a local display time without losing all-day/floating semantics."""
    if moment is None:
        return ''
    if moment['kind'] == 'date':
        return moment['value']
    value = datetime.fromisoformat(moment['value'])
    if moment['kind'] == 'utc':
        value = value.astimezone()
    return value.strftime('%Y-%m-%d %H:%M')


def _property(line: str) -> tuple[str, dict, str]:
    # Linear scanning avoids a quadratic quoted-delimiter regular expression.
    if len(line) > 8192:
        raise ValueError('Calendar property exceeds 8192 characters')
    parts, start, quoted, value = [], 0, False, None
    for index, character in enumerate(line):
        if character == '"':
            quoted = not quoted
        elif not quoted and character in ';:':
            parts.append(line[start:index])
            start = index + 1
            if character == ':':
                value = line[start:]
                break
    if value is None or quoted:
        raise ValueError('Invalid calendar content line')
    parameters = {}
    for part in parts[1:]:
        key, separator, parameter = part.partition('=')
        if not separator or key.upper() in parameters:
            raise ValueError('Invalid calendar property parameter')
        parameters[key.upper()] = parameter.strip('"').upper() if key.upper() == 'VALUE' else parameter.strip('"')
    return parts[0].upper(), parameters, value


def _duration(value: str) -> timedelta:
    match = re.fullmatch(r'P(?:(\d+)W|(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?)', value)
    if not match or not any(match.groups()):
        raise ValueError('Unsupported calendar duration')
    weeks, days, hours, minutes, seconds = (int(part or 0) for part in match.groups())
    if max(weeks, days, hours, minutes, seconds) > 100000:
        raise ValueError('Calendar duration is too large')
    delta = timedelta(weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds)
    if not timedelta(0) < delta <= timedelta(days=3660):
        raise ValueError('Calendar duration must be positive and within ten years')
    return delta


def _entry(kind: str, fields: dict) -> dict:
    if 'RECURRENCE-ID' in fields and 'RANGE' in fields['RECURRENCE-ID'][0]:
        raise ValueError('Calendar recurrence RANGE is unsupported')
    unsupported = {'RRULE', 'RDATE', 'EXDATE', 'EXRULE'} & fields.keys()
    if unsupported:
        raise ValueError('Recurring calendars are unsupported; export individual occurrences')
    uid = unescape(fields.get('UID', ({}, ''))[1])
    if not uid or len(uid) > 1000:
        raise ValueError('Calendar events/tasks require UID (up to 1000 characters)')
    cancelled = fields.get('STATUS', ({}, ''))[1].upper() == 'CANCELLED'
    title = unescape(fields.get('SUMMARY', ({}, 'Cancelled' if cancelled else ''))[1])
    description = unescape(fields.get('DESCRIPTION', ({}, ''))[1])
    if not title.strip() or len(title) > 1000 or len(description) > 2000:
        raise ValueError('Calendar title/description is missing or too long')
    start = parse_time(fields['DTSTART'][1], fields['DTSTART'][0]) if 'DTSTART' in fields else None
    finish_key = 'DTEND' if kind == 'VEVENT' else 'DUE'
    finish = parse_time(fields[finish_key][1], fields[finish_key][0]) if finish_key in fields else None
    if kind == 'VEVENT' and start is None and not cancelled:
        raise ValueError('Calendar event requires DTSTART')
    if 'DURATION' in fields:
        if finish is not None or start is None:
            raise ValueError('DURATION requires DTSTART and cannot accompany DTEND/DUE')
        delta = _duration(fields['DURATION'][1])
        if start['kind'] == 'date' and delta.seconds:
            raise ValueError('All-day duration requires whole days')
        finish = _duration_end(start, fields['DTSTART'], delta)
    if finish is not None and start is not None:
        if finish['kind'] != start['kind'] or finish['value'] <= start['value']:
            raise ValueError('Calendar end must follow start with matching value type')
    recurrence = parse_time(fields['RECURRENCE-ID'][1], fields['RECURRENCE-ID'][0]) if 'RECURRENCE-ID' in fields else None
    identity = hashlib.sha256((kind + '\0' + uid + '\0' + str(recurrence)).encode('utf-8')).hexdigest()
    sequence = fields.get('SEQUENCE', ({}, '0'))[1]
    if not sequence.isdigit() or len(sequence) > 9:
        raise ValueError('Invalid calendar SEQUENCE')
    status = fields.get('STATUS', ({}, ''))[1].upper()
    return dict(id=identity, title=title, description=description, kind='event' if kind == 'VEVENT' else 'task',
                start=start, due=finish, done=status == 'COMPLETED', sequence=int(sequence), cancelled=status == 'CANCELLED')


def _duration_end(start: dict, original: tuple, delta: timedelta) -> dict:
    parameters, source = original
    value = date.fromisoformat(start['value']) if start['kind'] == 'date' else datetime.fromisoformat(start['value'])
    if parameters.get('TZID'):
        wall = datetime.strptime(source, '%Y%m%dT%H%M%S') + timedelta(days=delta.days)
        value = datetime.fromisoformat(parse_time(wall.strftime('%Y%m%dT%H%M%S'), parameters)['value'])
        delta = timedelta(seconds=delta.seconds)
    return {'kind': start['kind'], 'value': (value + delta).isoformat()}


def parse_calendar(data: bytes) -> list[dict]:
    """Unfold UTF-8 lines; collect VEVENT/VTODO, reject malformed/unsupported import atomically."""
    if len(data) > MAX_CALENDAR_BYTES:
        raise ValueError('Calendar exceeds four MiB')
    text = re.sub(rb'\r?\n[ \t]', b'', data).decode('utf-8-sig')
    if '\x00' in text:
        raise ValueError('Calendar contains a NUL character')
    stack, fields, entries = [], {}, []
    for line in text.splitlines():
        if not line:
            continue
        name, parameters, value = _property(line)
        if name in ('BEGIN', 'END'):
            value = value.upper()
        if name == 'BEGIN':
            if not stack and value != 'VCALENDAR':
                raise ValueError('Expected VCALENDAR')
            stack.append(value)
            if value in ('VEVENT', 'VTODO'):
                if len(stack) != 2:
                    raise ValueError('Invalid nested calendar event')
                fields = {}
        elif name == 'END':
            if not stack or stack.pop() != value:
                raise ValueError('Unbalanced calendar components')
            if value in ('VEVENT', 'VTODO'):
                entries.append(_entry(value, fields))
                if len(entries) > 500:
                    raise ValueError('Calendar contains more than 500 items')
        elif stack and stack[-1] in ('VEVENT', 'VTODO') and name in {
                'UID', 'SUMMARY', 'DESCRIPTION', 'DTSTART', 'DTEND', 'DUE', 'DURATION',
                'RECURRENCE-ID', 'SEQUENCE', 'STATUS', 'RRULE', 'RDATE', 'EXDATE', 'EXRULE'}:
            if name in fields:
                raise ValueError('Duplicate calendar property: ' + name)
            fields[name] = parameters, value
        elif not stack:
            raise ValueError('Property outside calendar')
    if stack or not entries:
        raise ValueError('Calendar is incomplete or has no supported events/tasks')
    return entries
