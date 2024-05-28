import traceback
from typing import Callable

from PySide6 import QtCore
from PySide6.QtCore import Signal, QRunnable, Slot


class QThreadSignal(QtCore.QObject):
    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    progress = Signal(int)


class QThreadWorker(QRunnable):

    def __init__(self, function: Callable, *args, **kwargs):
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.signal = QThreadSignal()

    @Slot()
    def run(self):
        try:
            result = self.function(*self.args, **self.kwargs)
        except Exception as e:
            traceback.print_exc()
            self.signal.error.emit(e)
        else:
            self.signal.result.emit(result)
        finally:
            self.signal.finished.emit()
