"""Bounded UTF-8 file feeds; all filesystem access happens in a Qt worker."""
from __future__ import annotations

import csv
import io
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Qt, Signal

from frontengine.utils.multi_language.retranslate import translate
from frontengine.utils.power_mode.power_mode import scaled_interval

MAX_FILE_BYTES = 1024 * 1024
MAX_TEXT_CHARS = 65536


@dataclass(frozen=True)
class FileTextResult:
    """Status codes remain separate from translated presentation strings."""

    status: str
    value: str = ""
    fields: tuple[str, ...] = ()
    signature: tuple | None = None


def _json_fields(data) -> tuple[str, ...]:
    pending, fields = [("", data, 0)], []
    while pending and len(fields) < 256:
        path, value, depth = pending.pop()
        if depth > 32:
            raise ValueError("JSON nesting exceeds limit")
        if isinstance(value, dict):
            children = list(value.items())[:256]
        elif isinstance(value, list):
            children = list(enumerate(value))[:256]
        else:
            fields.append(path)
            continue
        pending.extend((path + "/" + str(key).replace("~", "~0").replace("/", "~1"), child, depth + 1)
                       for key, child in reversed(children))
    return tuple(fields)


def _select_json(data, field: str):
    if not field:
        return data
    if not field.startswith("/"):
        raise KeyError(field)
    for token in field[1:].split("/"):
        key = token.replace("~1", "/").replace("~0", "~")
        if isinstance(data, dict):
            data = data[key]
        elif isinstance(data, list) and key.isdecimal():
            data = data[int(key)]
        else:
            raise KeyError(field)
    return data


def _invalid_json_constant(_value: str) -> None:
    raise ValueError("JSON requires finite values")


def _parse_file(text: str, suffix: str, field: str) -> tuple[str, tuple[str, ...]]:
    if suffix == ".txt":
        return text, ()
    if suffix == ".json":
        data = json.loads(text, parse_constant=_invalid_json_constant)
        fields = _json_fields(data)
        selected = _select_json(data, field)
        return (selected if isinstance(selected, str) else json.dumps(selected, ensure_ascii=False)), fields
    rows = csv.reader(io.StringIO(text), strict=True)
    header = next(rows, [])
    if not header or len(header) > 256 or not all(header) or len(set(header)) != len(header):
        raise ValueError("CSV requires unique headers")
    if field and field not in header:
        raise KeyError(field)
    index, values = header.index(field) if field else None, []
    for row in rows:
        if len(row) != len(header):
            raise ValueError("CSV row/header mismatch")
        if index is not None:
            values.append(row[index])
    return "\n".join(values) if field else text, tuple(header)


def read_file_text(path: str, field: str = "", previous: FileTextResult | None = None) -> FileTextResult:
    """Read a regular UTF-8 TXT/JSON/CSV file, reporting recoverable errors."""
    try:
        source = Path(path)
        if not path or source.suffix.lower() not in (".txt", ".json", ".csv"):
            return FileTextResult("unsupported")
        if not stat.S_ISREG(source.stat().st_mode):
            return FileTextResult("unsupported")
        flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
        with os.fdopen(os.open(source, flags), "rb") as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode):
                return FileTextResult("unsupported")
            if metadata.st_size > MAX_FILE_BYTES:
                return FileTextResult("too_large")
            signature = (str(source.absolute()), field, metadata.st_mtime_ns, metadata.st_size,
                         metadata.st_ino, metadata.st_ctime_ns)
            if previous and previous.signature == signature and previous.status == "ready":
                return previous
            content = stream.read(MAX_FILE_BYTES + 1)
        if len(content) > MAX_FILE_BYTES:
            return FileTextResult("too_large")
        text = content.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
        value, fields = _parse_file(text, source.suffix.lower(), field)
        if len(value) > MAX_TEXT_CHARS:
            return FileTextResult("too_large")
        return FileTextResult("ready", value, fields, signature)
    except FileNotFoundError:
        return FileTextResult("missing")
    except (KeyError, IndexError):
        return FileTextResult("missing_field")
    except (UnicodeError, ValueError, csv.Error, RecursionError):
        return FileTextResult("invalid")
    except OSError:
        return FileTextResult("read_error")


class _FileSignals(QObject):
    finished = Signal(object)


class _FileJob(QRunnable):
    def __init__(self, reader: Callable, arguments: tuple, signals: _FileSignals) -> None:
        super().__init__()
        self.reader, self.arguments, self.signals = reader, arguments, signals

    def run(self) -> None:
        try:
            result = self.reader(*self.arguments)
        except Exception as error:  # Worker boundary must always release the pending read.
            from frontengine.utils.logging.loggin_instance import front_engine_logger
            front_engine_logger.warning(f"Local file reader failed: {type(error).__name__}")
            result = FileTextResult("read_error")
        self.signals.finished.emit(result)


class LocalFileTextSource(QObject):
    """One pending read per feed; stop ignores late results without blocking Qt."""

    changed = Signal()
    result_changed = Signal(object)
    kind = "local_file"
    refresh_interval_ms = 0

    def __init__(self, path: str, field: str = "", interval_ms: int = 1000, parent=None,
                 reader: Callable = read_file_text) -> None:
        super().__init__(parent)
        self.path, self.field, self.reader = path, field, reader
        try:
            self.interval_ms = max(500, min(3600000, int(interval_ms)))
        except (ValueError, TypeError, OverflowError):
            self.interval_ms = 1000
        self.result = FileTextResult("loading")
        self.pending = None
        self.closed = False
        self.timer = QTimer(self)
        self.timer.setInterval(self.interval_ms)
        self.timer.timeout.connect(self.refresh)

    def start(self) -> None:
        """Start asynchronous reads; repeated start is harmless."""
        if not self.closed:
            self.timer.start()
            self.refresh()

    def refresh(self) -> None:
        """Schedule one bounded read without doing filesystem work on the UI thread."""
        if self.closed or self.pending is not None:
            return
        self.pending = _FileSignals()
        self.pending.finished.connect(self._finished, Qt.ConnectionType.QueuedConnection)
        QThreadPool.globalInstance().start(_FileJob(
            self.reader, (self.path, self.field, self.result), self.pending))

    def _finished(self, result: FileTextResult) -> None:
        self.pending = None
        if self.closed:
            return
        if result != self.result:
            self.result = result
            self.result_changed.emit(result)
            self.changed.emit()

    def text(self) -> str:
        """Ready content or an explicit translated status for the overlay."""
        return self.result.value if self.result.status == "ready" else translate("text_file_" + self.result.status)

    def set_low_power(self, enabled: bool) -> None:
        """Apply the same quality-aware polling delay used by text overlays."""
        self.timer.setInterval(scaled_interval(self.interval_ms, enabled))

    def stop(self) -> None:
        """Stop polling and suppress completion callbacks during teardown."""
        self.closed = True
        self.timer.stop()
