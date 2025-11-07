import logging
import queue
import sys

from frontengine.utils.logging.loggin_instance import front_engine_logger


class RedirectStdOut(logging.Handler):
    """Redirect stdout to queue"""

    def __init__(self):
        super().__init__()

    def write(self, content_to_write: str) -> None:
        if content_to_write.strip():  # 避免空行
            redirect_manager_instance.std_out_queue.put(str(content_to_write))

    def flush(self) -> None:
        # 保持與 file-like 介面一致
        pass

    def emit(self, record: logging.LogRecord) -> None:
        redirect_manager_instance.std_out_queue.put(self.format(record))


class RedirectStdErr(logging.Handler):
    """Redirect stderr to queue"""

    def __init__(self):
        super().__init__()

    def write(self, content_to_write: str) -> None:
        if content_to_write.strip():
            redirect_manager_instance.std_err_queue.put(str(content_to_write))

    def flush(self) -> None:
        pass

    def emit(self, record: logging.LogRecord) -> None:
        redirect_manager_instance.std_err_queue.put(self.format(record))


class RedirectManager:
    """Redirect all stdout/stderr and logging output to queues"""

    def __init__(self):
        front_engine_logger.info("Init RedirectManager")
        self.std_err_queue = queue.Queue()
        self.std_out_queue = queue.Queue()

    @staticmethod
    def set_redirect() -> None:
        """Redirect stdout/stderr and attach logging handlers"""
        front_engine_logger.info("RedirectManager set_redirect")

        redirect_out = RedirectStdOut()
        redirect_err = RedirectStdErr()

        sys.stdout = redirect_out
        sys.stderr = redirect_err

        default_logger = logging.getLogger("FrontEngine_RedirectManager")
        if redirect_err not in default_logger.handlers:
            default_logger.addHandler(redirect_err)

        skip_logger_list = [
            "JEditor", "FrontEngine", "AutomationIDE",
            "TestPioneer", "langchain", "langchain_core", "langchain_openai"
        ]

        for name in logging.root.manager.loggerDict.keys():
            if name not in skip_logger_list:
                logger = logging.getLogger(name)
                if redirect_err not in logger.handlers:
                    logger.addHandler(redirect_err)

    @staticmethod
    def restore_std() -> None:
        """Restore original stdout/stderr"""
        front_engine_logger.info("RedirectManager restore_std")
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__


redirect_manager_instance = RedirectManager()