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


class PetBuiltinInstall(QRunnable):
    """Draw one built-in character and its wardrobe off the GUI thread, then install them."""

    def __init__(self, library, identifier):
        super().__init__()
        self.library, self.identifier = library, identifier
        self.cancel = Event()
        self.signals = InstallSignals()

    def run(self) -> None:
        from frontengine.show.pet.inkside.library import install_builtin
        error = ''
        try:
            install_builtin(self.library, self.identifier, self.cancel)
        except (OSError, ValueError) as failure:
            error = str(failure)
        self.signals.finished.emit(error)
