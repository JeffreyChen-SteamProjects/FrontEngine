"""Worker-owned SQLite image payloads with bounded storage and explicit opt-in."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import sqlite3

from PySide6.QtCore import QBuffer, QIODevice, Qt
from PySide6.QtGui import QImage, QImageReader

MAX_IMAGE_PIXELS = 16_777_216
MAX_IMAGE_BYTES = 8 * 1024 * 1024


def encode_image(image: QImage) -> bytes:
    """Encode on a worker; clipboard images never produce GUI-thread PNG compression."""
    if image.isNull() or image.width() * image.height() > MAX_IMAGE_PIXELS:
        raise ValueError('History images must be valid and within 16 megapixels')
    detached = image.copy()
    detached.setDevicePixelRatio(1)
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not detached.save(buffer, 'PNG'):
        raise ValueError('Image could not be encoded')
    data = bytes(buffer.data())
    buffer.close()
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError('Encoded history image exceeds eight MiB')
    return data


class ImageHistoryRepository:
    """One-thread repository; memory-only until explicit file persistence is selected."""

    def __init__(self, path: str | Path, *, persistent: bool = False,
                 limit: int = 50, capacity_mib: int = 64) -> None:
        self.path = Path(path).absolute()
        self.connection = None
        self.persistent = False
        self.limit, self.capacity = self._limits(limit, capacity_mib)
        self.connection = self._open(self.path if persistent else None)
        self.persistent = persistent
        try:
            with self.connection:
                self._trim()
        except Exception:
            self.close()
            raise

    @staticmethod
    def _limits(limit: int, capacity_mib: int) -> tuple[int, int]:
        if type(limit) is not int or not 10 <= limit <= 200 or type(capacity_mib) is not int or not 8 <= capacity_mib <= 128:
            raise ValueError('History capacity must be 10–200 images and 8–128 MiB')
        return limit, capacity_mib * 1024 * 1024

    def _open(self, path: Path | None):
        if path is not None and (path.is_symlink() or not path.parent.is_dir()):
            raise ValueError('History database requires a regular file in an existing directory')
        if path is not None and path.exists() and path.stat().st_size > 132 * 1024 * 1024:
            raise ValueError('History database exceeds 132 MiB')
        connection = sqlite3.connect(str(path) if path is not None else ':memory:')
        try:
            connection.execute('PRAGMA auto_vacuum=FULL')
            connection.execute('PRAGMA max_page_count=33792')  # <=132 MiB including index overhead.
            connection.execute('PRAGMA cache_size=-2048')
            version = connection.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1):
                raise ValueError('Unsupported image history database version')
            connection.execute('CREATE TABLE IF NOT EXISTS images (id TEXT PRIMARY KEY, at TEXT NOT NULL, pinned INTEGER NOT NULL, png BLOB NOT NULL, text TEXT NOT NULL DEFAULT "")')
            connection.execute('PRAGMA user_version=1')
            connection.commit()
            return connection
        except Exception:
            connection.close()
            raise

    def _trim(self, *, protect: str = '', connection=None, limit=None, capacity=None) -> None:
        connection = connection or self.connection
        limit = self.limit if limit is None else limit
        capacity = self.capacity if capacity is None else capacity
        count, used = connection.execute('SELECT count(*), coalesce(sum(length(png)),0) FROM images').fetchone()
        while count > limit or used > capacity:
            row = connection.execute('SELECT id,length(png) FROM images WHERE pinned=0 AND id<>? ORDER BY at ASC,id ASC LIMIT 1', (protect,)).fetchone()
            if row is None:
                raise ValueError('Pinned images fill history capacity; unpin or remove an image')
            connection.execute('DELETE FROM images WHERE id=?', (row[0],))
            count, used = count-1, used-row[1]

    def add(self, image: QImage, *, text: str = '', at: str | None = None) -> str:
        """Deduplicate content, retain pin state and atomically evict only unpinned images."""
        if not isinstance(text, str) or len(text) > 20000:
            raise ValueError('History OCR text exceeds 20000 characters')
        data = encode_image(image)
        identity = hashlib.sha256(data).hexdigest()
        timestamp = at or datetime.now(timezone.utc).isoformat(timespec='microseconds')
        datetime.fromisoformat(timestamp)
        with self.connection:
            existing = self.connection.execute('SELECT 1 FROM images WHERE id=?', (identity,)).fetchone()
            if existing is None:
                self._trim(limit=self.limit-1, capacity=self.capacity-len(data))
            self.connection.execute('INSERT INTO images(id,at,pinned,png,text) VALUES(?,?,0,?,?) ON CONFLICT(id) DO UPDATE SET at=excluded.at,text=CASE WHEN excluded.text="" THEN images.text ELSE excluded.text END', (identity, timestamp, data, text))
            self._trim(protect=identity)
        return identity

    def entries(self, *, text: str = '', date: str = '') -> list[dict]:
        """Return bounded metadata and thumbnails; full images stay outside UI lists."""
        rows = self.connection.execute('SELECT id,at,pinned,text FROM images ORDER BY pinned DESC,at DESC,id DESC LIMIT 200').fetchall()
        result = []
        for identity, at, pinned, recognized in rows:
            if not isinstance(identity, str) or len(identity) != 64 or not isinstance(at, str) or len(at) > 64 or not isinstance(recognized, str) or len(recognized) > 20000 or pinned not in (0, 1):
                raise ValueError('Saved history metadata is invalid')
            local_date = datetime.fromisoformat(at).astimezone().date().isoformat()
            if text.casefold() not in recognized.casefold() or (date and local_date != date):
                continue
            image = self.image(identity)
            thumbnail = image.scaled(160, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            result.append(dict(id=identity, at=at, pinned=bool(pinned), text=recognized, thumbnail=thumbnail))
        return result

    def image(self, identity: str) -> QImage:
        """Decode one bounded PNG; reject malformed database content explicitly."""
        row = self.connection.execute('SELECT png FROM images WHERE id=? AND length(png)<=?', (identity, MAX_IMAGE_BYTES)).fetchone()
        if row is None:
            raise ValueError('History image was removed or exceeds its size limit')
        if hashlib.sha256(row[0]).hexdigest() != identity:
            raise ValueError('History image digest is invalid')
        buffer = QBuffer()
        buffer.setData(row[0])
        buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        reader = QImageReader(buffer, b'PNG')
        size = reader.size()
        if not 0 < size.width() * size.height() <= MAX_IMAGE_PIXELS:
            raise ValueError('Saved history image dimensions are invalid or too large')
        image = reader.read()
        buffer.close()
        if image.isNull() or image.width() * image.height() > MAX_IMAGE_PIXELS:
            raise ValueError('Saved history image is invalid or too large')
        image.setDevicePixelRatio(1)
        return image

    def set_pinned(self, identity: str, value: bool) -> None:
        """Pins protect against eviction but never raise capacity limits."""
        with self.connection:
            self.connection.execute('UPDATE images SET pinned=? WHERE id=?', (int(bool(value)), identity))

    def remove(self, identity: str) -> None:
        """Delete the image and its OCR text together."""
        with self.connection:
            self.connection.execute('DELETE FROM images WHERE id=?', (identity,))

    def clear(self) -> None:
        """Erase all images including pins; VACUUM releases retained database payload pages."""
        with self.connection:
            self.connection.execute('DELETE FROM images')
        self.connection.execute('VACUUM')

    def configure(self, *, persistent: bool, limit: int, capacity_mib: int) -> None:
        """Validate new bounds atomically; opting out deletes the previous persistent file."""
        new_limit, new_capacity = self._limits(limit, capacity_mib)
        if persistent == self.persistent:
            with self.connection:
                self._trim(limit=new_limit, capacity=new_capacity)
            self.limit, self.capacity = new_limit, new_capacity
            return
        target = self._open(self.path if persistent else None)
        try:
            rows = self.connection.execute('SELECT id,at,pinned,png,text FROM images').fetchall()
            with target:
                target.executemany('INSERT INTO images(id,at,pinned,png,text) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET at=max(images.at,excluded.at),pinned=max(images.pinned,excluded.pinned)', rows)
                self._trim(connection=target, limit=new_limit, capacity=new_capacity)
        except Exception:
            target.close()
            raise
        old = self.connection
        if self.persistent and not persistent:
            self.clear()
        old.close()
        self.connection, self.persistent = target, persistent
        self.limit, self.capacity = new_limit, new_capacity
        if not persistent:
            self.path.unlink(missing_ok=True)

    def close(self) -> None:
        """Release the worker's database handle and in-memory payloads."""
        if self.connection is not None:
            self.connection.close()
            self.connection = None
