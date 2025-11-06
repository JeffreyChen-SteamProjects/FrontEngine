import traceback
from typing import Callable, Any

from PySide6 import QtCore
from PySide6.QtCore import Signal, QRunnable, Slot


class QThreadSignal(QtCore.QObject):
    """
    定義執行緒的訊號
    Define signals for thread worker
    """
    finished = Signal()          # 任務完成 / Task finished
    error = Signal(Exception)    # 任務錯誤 / Task error
    result = Signal(object)      # 任務結果 / Task result
    progress = Signal(int)       # 任務進度 / Task progress


class QThreadWorker(QRunnable):
    """
    通用的執行緒工作類別
    Generic thread worker class
    """

    def __init__(self, function: Callable[..., Any], *args, **kwargs):
        """
        初始化執行緒工作
        Initialize thread worker

        :param function: 要執行的函式 (Function to execute)
        :param args: 傳入函式的參數 (Arguments for the function)
        :param kwargs: 傳入函式的關鍵字參數 (Keyword arguments for the function)
        """
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.signal = QThreadSignal()

    @Slot()
    def run(self) -> None:
        """
        執行緒主程式
        Thread main execution
        """
        try:
            result = self.function(*self.args, **self.kwargs)
        except Exception as e:
            traceback.print_exc()
            # 傳遞錯誤訊號
            # Emit error signal
            self.signal.error.emit(e)
        else:
            # 傳遞結果訊號
            # Emit result signal
            self.signal.result.emit(result)
        finally:
            # 傳遞完成訊號
            # Emit finished signal
            self.signal.finished.emit()