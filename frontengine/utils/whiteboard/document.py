"""Validate and atomically persist bounded canvas-coordinate stroke documents."""
from __future__ import annotations

from copy import deepcopy
import json
import math
from pathlib import Path
import re
from threading import Event

from PySide6.QtCore import QSaveFile, QIODevice

MAX_POINTS = 100_000
MAX_BYTES = 8 * 1024 * 1024


def blank_page() -> dict:
    """Create an independent blank page and view state."""
    return {'strokes': [], 'zoom': 1.0, 'offset': [0.0, 0.0]}


def _number(value, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError('Whiteboard coordinates, widths and zoom must be finite and bounded')
    return float(value)


def _pair(value) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError('Whiteboard coordinates must be pairs')
    return [_number(number, -100_000, 100_000) for number in value]


def _stroke(value: dict) -> dict:
    if not isinstance(value, dict) or not isinstance(value.get('points'), (list, tuple)) or not 2 <= len(value['points']) <= MAX_POINTS:
        raise ValueError('Each whiteboard stroke needs 2–100000 points')
    color = value.get('color')
    if not isinstance(color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
        raise ValueError('Whiteboard pen color must be #RRGGBB')
    return {'color': color, 'width': _number(value.get('width'), 1, 64),
            'points': [_pair(point) for point in value['points']]}


def normalize_document(value: dict) -> dict:
    """Reject malformed files before replacing an existing board or allocating images."""
    if not isinstance(value, dict) or type(value.get('version')) is not int or value['version'] != 1:
        raise ValueError('Unsupported whiteboard document version')
    pages, current = value.get('pages'), value.get('current')
    if not isinstance(pages, list) or not 1 <= len(pages) <= 50:
        raise ValueError('Whiteboard needs 1–50 pages')
    if type(current) is not int or not 0 <= current < len(pages):
        raise ValueError('Whiteboard current page is invalid')
    normalized, points = [], 0
    for page in pages:
        if not isinstance(page, dict) or not isinstance(page.get('strokes'), list) or len(page['strokes']) > 2000:
            raise ValueError('At most 2000 strokes per whiteboard page')
        for stroke in page['strokes']:
            if not isinstance(stroke, dict) or not isinstance(stroke.get('points'), (list, tuple)):
                raise ValueError('Whiteboard stroke points are invalid')
            points += len(stroke['points'])
        if points > MAX_POINTS:
            raise ValueError('Whiteboard exceeds 100000 total points')
        normalized.append({'strokes': [_stroke(stroke) for stroke in page['strokes']],
                           'zoom': _number(page.get('zoom', 1), .2, 5),
                           'offset': _pair(page.get('offset', [0, 0]))})
    return {'version': 1, 'current': current, 'pages': normalized}


def read_document(path: str) -> dict:
    """Read at most eight MiB and validate the complete document before returning it."""
    with Path(path).open('rb') as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('Whiteboard file exceeds eight MiB')
    return normalize_document(json.loads(data.decode('utf-8-sig')))


def write_document(value: dict, path: str, *, cancel: Event | None = None) -> str:
    """Publish a validated JSON snapshot atomically; cancellation preserves the target."""
    data = json.dumps(normalize_document(value), ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    if len(data) > MAX_BYTES:
        raise ValueError('Whiteboard document exceeds eight MiB')
    target = QSaveFile(path)
    if not target.open(QIODevice.OpenModeFlag.WriteOnly):
        raise OSError(target.errorString())
    try:
        if target.write(data) != len(data):
            raise OSError(target.errorString())
        if cancel is not None and cancel.is_set():
            raise InterruptedError('Whiteboard save cancelled')
        if not target.commit():
            raise OSError(target.errorString())
    except (OSError, ValueError):
        target.cancelWriting()
        raise
    return path


class WhiteboardDocument:
    """Keep independent page strokes and view states while preserving legacy access."""

    def __init__(self) -> None:
        self.pages = [blank_page()]
        self.current = 0
        self.history = []

    @property
    def page(self) -> dict:
        """The active mutable page, owned by the GUI thread."""
        return self.pages[self.current]

    def snapshot(self) -> dict:
        """Detach a file-worker snapshot; worker validation never touches Qt widgets."""
        return deepcopy({'version': 1, 'current': self.current, 'pages': self.pages})

    def replace(self, value: dict) -> None:
        """Validate first; failure leaves all existing pages unchanged."""
        normalized = normalize_document(value)
        self.pages, self.current = normalized['pages'], normalized['current']
        self.history.clear()

    def checkpoint(self) -> None:
        """Keep at most twenty detached active-page edit states across the document."""
        self.history.append((self.page, deepcopy(self.page['strokes'])))
        del self.history[:-20]

    def undo(self) -> bool:
        """Undo the most recent edit on this page without changing its viewport."""
        for index in reversed(range(len(self.history))):
            page, strokes = self.history[index]
            if page is self.page:
                page['strokes'] = strokes
                self.history.pop(index)
                return True
        return False

    def add_page(self) -> int:
        """Add a page up to the document limit and select it."""
        if len(self.pages) >= 50:
            raise ValueError('Whiteboard already has 50 pages')
        self.pages.append(blank_page())
        self.current = len(self.pages) - 1
        return self.current

    def remove_page(self) -> None:
        """Delete the active page; keep at least one blank page."""
        removed = self.pages.pop(self.current)
        self.history = [(page, strokes) for page, strokes in self.history if page is not removed]
        if not self.pages:
            self.pages.append(blank_page())
        self.current = min(self.current, len(self.pages) - 1)


def hit_stroke(strokes: list[dict], point: tuple[float, float], tolerance: float) -> int | None:
    """Select the topmost stroke by segment distance, independent of pan/zoom."""
    x, y = point
    for index in reversed(range(len(strokes))):
        stroke = strokes[index]
        radius = tolerance + stroke['width'] / 2
        for start, end in zip(stroke['points'], stroke['points'][1:]):
            dx, dy = end[0]-start[0], end[1]-start[1]
            length = dx*dx + dy*dy
            position = max(0, min(1, ((x-start[0])*dx+(y-start[1])*dy)/length)) if length else 0
            distance = (x-start[0]-position*dx)**2 + (y-start[1]-position*dy)**2
            if distance <= radius*radius:
                return index
    return None
