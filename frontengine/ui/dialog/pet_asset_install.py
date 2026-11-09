"""A cancellable asset-install job with GUI-thread result delivery."""
from threading import Event

from PySide6.QtCore import QObject, QRunnable, Signal


class InstallSignals(QObject):
    finished = Signal(str)


class PetAssetInstall(QRunnable):
    def __init__(self, library, source):
        super().__init__()
        self.library, self.source = library, source
        self.cancel = Event()
        self.signals = InstallSignals()

    def run(self) -> None:
        error = ''
        try:
            self.library.install(self.source, cancel=self.cancel)
        except (OSError, ValueError) as failure:
            error = str(failure)
        self.signals.finished.emit(error)


class PuppetExport(QRunnable):
    """Write a built-in character as a Puppet model and pet script off the GUI thread."""

    def __init__(self, identifier, folder):
        super().__init__()
        self.identifier, self.folder = identifier, folder
        self.signals = ExportSignals()

    def run(self) -> None:
        from frontengine.show.pet.inkside.puppet_export import export_puppet
        try:
            model, script = export_puppet(self.identifier, self.folder)
        except (OSError, ValueError) as failure:
            self.signals.finished.emit('', '', str(failure))
            return
        self.signals.finished.emit(str(model), str(script), '')


class ExportSignals(QObject):
    finished = Signal(str, str, str)


class BuiltinInstallSignals(InstallSignals):
    progress = Signal(int, int)


class PetBuiltinInstall(QRunnable):
    """Draw one built-in character and its wardrobe off the GUI thread, then install them."""

    def __init__(self, library, identifier):
        super().__init__()
        self.library, self.identifier = library, identifier
        self.cancel = Event()
        self.signals = BuiltinInstallSignals()

    def run(self) -> None:
        from frontengine.show.pet.inkside.library import install_builtin
        error = ''
        try:
            install_builtin(self.library, self.identifier, self.cancel, self.signals.progress.emit)
        except (OSError, ValueError) as failure:
            error = str(failure)
        self.signals.finished.emit(error)


class CharacterSignals(QObject):
    finished = Signal(str, str)   # character identifier, error
    wardrobe = Signal(str)        # the wardrobe that follows: error, empty when installed


class PetBuiltinCharacter(QRunnable):
    """Install a built-in character so a desktop pet can wear it.

    The character alone comes first, so the pet can appear at once; its wardrobe follows in the
    same job and reports separately. Cancelling stops whichever part is running.
    """

    def __init__(self, library, identifier):
        super().__init__()
        self.library, self.identifier = library, identifier
        self.cancel = Event()
        self.signals = CharacterSignals()
        self.done = False

    def run(self) -> None:
        if self._character():
            self._wardrobe()
        self.done = True

    def _wardrobe(self) -> None:
        from frontengine.show.pet.inkside.library import install_builtin
        error = ''
        if not self.cancel.is_set():
            try:
                install_builtin(self.library, self.identifier, self.cancel)
            except (OSError, ValueError) as failure:      # the wardrobe installs it again when opened
                error = str(failure)
        self.signals.wardrobe.emit(error)

    def _character(self) -> bool:
        from frontengine.show.pet.inkside.library import VERSION, install_builtin
        try:
            install_builtin(self.library, self.identifier, self.cancel, wardrobe=False)
            catalog, _errors = self.library.scan()
            catalog.resolve({'id': self.identifier, 'version': VERSION}, 'character')
        except (OSError, ValueError) as failure:
            self.signals.finished.emit(self.identifier, str(failure))
            return False
        self.signals.finished.emit(self.identifier, '')
        return True
