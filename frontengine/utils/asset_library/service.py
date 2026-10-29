"""One lazy asset file job and one polled result; no GUI-thread decoding/scanning."""
from copy import deepcopy
from pathlib import Path
from threading import Event, Lock, Thread

from PySide6.QtCore import QObject, QTimer, Signal

from frontengine.utils.asset_library.repository import AssetRepository
from frontengine.utils.asset_library.references import list_references, plan_relink, commit_relink, recover_relink
from frontengine.utils.asset_library.file_lock import catalog_lock


class AssetLibraryService(QObject):
    """Serialize explicit catalog actions and bound delivery to one result slot."""
    result = Signal(str, object)
    failed = Signal(str, str)
    started = Signal(str)

    def __init__(self, root: str | Path, parent=None) -> None:
        super().__init__(parent)
        self.root, self.busy = Path(root).absolute(), False
        self.cancelled, self.lock, self.mailbox = Event(), Lock(), None
        self.thread = None
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self._poll)

    def request(self, action: str, **arguments) -> bool:
        """Accept one action without replacing a user mutation with another request."""
        fields = {'list': {'text', 'favorites'}, 'add': {'path'}, 'edit': {'identity', 'tags', 'favorite'},
                  'remove': {'identity'}, 'references': {'identity', 'scene'},
                  'plan': {'identity', 'replacement', 'scene'}, 'commit': {'plan'}}
        if action not in fields or set(arguments) != fields[action]:
            raise ValueError('Invalid asset library operation')
        if self.busy or self.cancelled.is_set():
            return False
        self.busy = True
        self.started.emit(action)
        self.timer.start()
        self.thread = Thread(target=self._run, args=(action, deepcopy(arguments)), name='FrontEngineAssets', daemon=True)
        self.thread.start()
        return True

    def _run(self, action: str, arguments: dict) -> None:
        try:
            with catalog_lock(self.root):
                recover_relink(self.root)
                repository = AssetRepository(self.root)
                value = self._execute(repository, action, arguments)
            result = value, ''
        except Exception as error:
            result = None, str(error)[:2000]
        with self.lock:
            if not self.cancelled.is_set():
                self.mailbox = action, result

    def _execute(self, repository: AssetRepository, action: str, arguments: dict):
        if self.cancelled.is_set():
            raise ValueError('Asset operation cancelled')
        if action == 'list':
            return repository.entries(**arguments)
        if action == 'add':
            return repository.add(arguments['path'])
        if action == 'edit':
            repository.edit(**arguments)
        elif action == 'remove':
            repository.remove(**arguments)
        elif action == 'references':
            return list_references(repository, **arguments)
        elif action == 'plan':
            return plan_relink(repository, **arguments)
        elif action == 'commit':
            commit_relink(repository, arguments['plan'], cancelled=self.cancelled)
        return True

    def _poll(self) -> None:
        with self.lock:
            result, self.mailbox = self.mailbox, None
        if result is None:
            return
        self.busy = False
        self.timer.stop()
        action, (value, error) = result
        if error:
            self.failed.emit(action, error)
        else:
            self.result.emit(action, value)

    def stop(self) -> None:
        """Cancel pending repair writes, ignore late results and return without a GUI wait."""
        self.cancelled.set()
        self.timer.stop()
        with self.lock:
            self.mailbox = None
