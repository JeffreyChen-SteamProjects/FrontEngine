"""Bounded clipboard acquisition and one worker-owned local image repository."""
from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
import re
import sqlite3
from threading import Condition, Thread
from typing import Callable

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QGuiApplication, QImage

from frontengine.utils.image_history.repository import ImageHistoryRepository, MAX_IMAGE_PIXELS, encode_image


class _Worker:
    def __init__(self, path: Path, config: dict, indexer: Callable | None = None) -> None:
        self.path, self.config = path, dict(config)
        self.indexer = indexer
        self.condition = Condition()
        self.commands, self.results = OrderedDict(), OrderedDict()
        self.image, self.stopping = None, False
        self.dropped = 0
        self.thread = Thread(target=self.run, name='FrontEngineImageHistory', daemon=True)
        self.thread.start()

    def submit(self, kind: str, arguments: dict) -> None:
        with self.condition:
            if not self.stopping:
                self.commands[kind] = arguments
                self.condition.notify()

    def capture(self, image: QImage) -> None:
        with self.condition:
            if not self.stopping:
                self.dropped += int(self.image is not None)
                self.image = image.copy()
                self.condition.notify()

    def stop(self) -> None:
        with self.condition:
            self.stopping, self.image = True, None
            self.commands.clear()
            self.results.clear()
            self.condition.notify()

    def take_results(self) -> list:
        with self.condition:
            results = list(self.results.items())
            self.results.clear()
            return results

    def run(self) -> None:
        repository = None
        try:
            while True:
                job = self._next()
                if job is None:
                    return
                kind, arguments = job
                try:
                    if repository is None:
                        config = arguments if kind == 'configure' else self.config
                        if kind == 'configure' and self.config['persistent'] and not config['persistent']:
                            if self.path.is_symlink():
                                raise ValueError('Refusing to remove a symlinked history database')
                            self.path.unlink(missing_ok=True)
                        repository = ImageHistoryRepository(self.path, persistent=config['persistent'],
                                                            limit=config['limit'], capacity_mib=config['capacity_mib'])
                    value = self._execute(repository, kind, arguments)
                    result = (value, '')
                except (OSError, ValueError, sqlite3.Error, RuntimeError) as error:
                    result = (None, str(error)[:2000])
                with self.condition:
                    if not self.stopping:
                        self.results[kind] = result
        except (OSError, ValueError, sqlite3.Error) as error:
            with self.condition:
                if not self.stopping:
                    self.results['startup'] = (None, str(error)[:2000])
        finally:
            if repository is not None:
                repository.close()

    def _next(self):
        with self.condition:
            while not self.stopping and not self.commands and self.image is None:
                self.condition.wait()
            if self.stopping:
                return None
            if self.commands:
                return self.commands.popitem(last=False)
            image, self.image = self.image, None
            return 'capture', {'image': image}

    def _execute(self, repository: ImageHistoryRepository, kind: str, args: dict):
        if kind == 'configure':
            repository.configure(persistent=args['persistent'], limit=args['limit'], capacity_mib=args['capacity_mib'])
            self.config = dict(args)
            if not args['enabled']:
                with self.condition:
                    self.image = None
            return dict(args)
        if kind == 'list':
            return repository.entries(**args)
        if kind == 'image':
            return {'id': args['id'], 'action': args['action'], 'image': repository.image(args['id'])}
        if kind == 'pin':
            repository.set_pinned(args['id'], args['value'])
        elif kind == 'remove':
            repository.remove(args['id'])
        elif kind == 'clear':
            with self.condition:
                self.image = None
            repository.clear()
        elif kind == 'capture':
            if not self.config['enabled']:
                return None
            return self._capture(repository, args['image'])
        else:
            raise ValueError('Unknown image history operation')
        return True

    def _capture(self, repository: ImageHistoryRepository, image: QImage):
        text, error = '', ''
        if self.indexer is not None:
            try:
                result = self.indexer(encode_image(image))
                if result.status != 'success':
                    error = result.error or result.status
                elif not isinstance(result.text, str) or len(result.text) > 20000:
                    error = 'Local OCR text exceeds 20000 characters'
                else:
                    text = result.text
            except Exception as failure:
                error = str(failure)[:2000]
        identity = repository.add(image, text=text)
        return {'id': identity, 'indexed': self.indexer is not None and not error, 'error': str(error)[:2000]}


class ImageHistoryService(QObject):
    """Do no clipboard reads until enabled; coalesce compression and result delivery."""

    result = Signal(str, object)
    failed = Signal(str, str)

    def __init__(self, path: str | Path, config: dict | None = None, parent=None,
                 *, clipboard_provider: Callable = QGuiApplication.clipboard,
                 indexer: Callable | None = None) -> None:
        super().__init__(parent)
        source = config or {}
        self.config = {'enabled': source.get('enabled') is True, 'persistent': source.get('persistent') is True,
                       'limit': source.get('limit', 50), 'capacity_mib': source.get('capacity_mib', 64)}
        if type(self.config['limit']) is not int or not 10 <= self.config['limit'] <= 200:
            self.config['limit'] = 50
        if type(self.config['capacity_mib']) is not int or not 8 <= self.config['capacity_mib'] <= 128:
            self.config['capacity_mib'] = 64
        self.path = Path(path)
        self.indexer = indexer
        self.clipboard_provider, self.clipboard = clipboard_provider, None
        self.worker, self.closed = None, False
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self._poll)
        if self.config['enabled'] or self.config['persistent']:
            self._ensure_worker()
            self._watch(self.config['enabled'])

    def _ensure_worker(self) -> None:
        if self.closed:
            raise ValueError('Image history service is closed')
        if self.worker is None:
            self.worker = _Worker(self.path, self.config, self.indexer)
            self.timer.start()

    def request(self, kind: str, **arguments) -> None:
        """Queue one newest command per kind; external image output remains explicit."""
        if kind not in ('configure', 'list', 'image', 'pin', 'remove', 'clear'):
            raise ValueError('Unsupported image history command')
        self._validate_request(kind, arguments)
        self._ensure_worker()
        self.worker.submit(kind, dict(arguments))

    @staticmethod
    def _validate_request(kind: str, args: dict) -> None:
        fields = {'configure': {'enabled', 'persistent', 'limit', 'capacity_mib'},
                  'list': {'text', 'date'}, 'image': {'id', 'action'},
                  'pin': {'id', 'value'}, 'remove': {'id'}, 'clear': set()}
        if set(args) - fields[kind] or (kind not in ('list', 'clear') and set(args) != fields[kind]):
            raise ValueError('Image history request fields are invalid')
        if kind == 'configure':
            if type(args['enabled']) is not bool or type(args['persistent']) is not bool:
                raise ValueError('History enabled/persistent must be booleans')
            ImageHistoryRepository._limits(args['limit'], args['capacity_mib'])
        if 'id' in args and (not isinstance(args['id'], str) or re.fullmatch('[0-9a-f]{64}', args['id']) is None):
            raise ValueError('Invalid history image identifier')
        if kind == 'image' and args['action'] not in ('copy', 'pin', 'board', 'preview'):
            raise ValueError('Unknown history image action')
        if kind == 'pin' and type(args['value']) is not bool:
            raise ValueError('History pin must be a boolean')
        if kind == 'list' and any(not isinstance(value, str) or len(value) > 256 for value in args.values()):
            raise ValueError('History search values must be short text')

    def capture(self, image: QImage) -> bool:
        """Accept one detached latest input only when opted in; never queue every change."""
        if self.closed or not self.config['enabled'] or image.isNull():
            return False
        if image.width() * image.height() > MAX_IMAGE_PIXELS:
            self.failed.emit('capture', 'History image exceeds 16 megapixels')
            return False
        self._ensure_worker()
        self.worker.capture(image)
        return True

    def _watch(self, enabled: bool) -> None:
        if self.clipboard is not None:
            try:
                self.clipboard.dataChanged.disconnect(self._changed)
            except (RuntimeError, TypeError):
                pass
            self.clipboard = None
        if enabled:
            self.clipboard = self.clipboard_provider()
            if self.clipboard is not None:
                self.clipboard.dataChanged.connect(self._changed)

    def _changed(self) -> None:
        if self.clipboard is not None and self.config['enabled']:
            image = self.clipboard.image()
            if not image.isNull():
                self.capture(image)

    def _poll(self) -> None:
        for kind, (value, error) in self.worker.take_results():
            if error:
                if kind == 'startup':
                    self._watch(False)
                    self.config['enabled'] = False
                self.failed.emit(kind, error)
                continue
            if kind == 'configure':
                self.config = value
                self._watch(self.config['enabled'])
            self.result.emit(kind, value)

    def stop(self) -> None:
        """Stop watching, drop queued pixels/results and request worker handle release."""
        self.closed = True
        self._watch(False)
        self.timer.stop()
        if self.worker is not None:
            self.worker.stop()
