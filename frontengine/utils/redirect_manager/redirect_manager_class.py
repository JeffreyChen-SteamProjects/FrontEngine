import logging
import queue
import sys

from frontengine.utils.logging.loggin_instance import front_engine_logger


class RedirectStdOut(logging.Handler):

    # redirect logging std output to queue

    def __init__(self):
        super().__init__()

    def write(self, content_to_write) -> None:
        redirect_manager_instance.std_out_queue.put(content_to_write)

    def emit(self, record: logging.LogRecord) -> None:
        redirect_manager_instance.std_out_queue.put(self.format(record))


class RedirectStdErr(logging.Handler):

    # redirect logging stderr output to queue

    def __init__(self):
        super().__init__()

    def write(self, content_to_write) -> None:
        redirect_manager_instance.std_err_queue.put(content_to_write)

    def emit(self, record: logging.LogRecord) -> None:
        redirect_manager_instance.std_err_queue.put(self.format(record))


class RedirectManager(object):
    # Redirect all output to queue
    def __init__(self):
        front_engine_logger.info("Init RedirectManager")
        self.std_err_queue = queue.Queue()
        self.std_out_queue = queue.Queue()

    @staticmethod
    def set_redirect() -> None:
        """
        :return: None
        """
        front_engine_logger.info("RedirectManager set_redirect")
        redirect_out = RedirectStdOut()
        redirect_err = RedirectStdErr()
        sys.stdout = redirect_out
        sys.stderr = redirect_err
        default_logger = logging.getLogger("RedirectManager")
        default_logger.addHandler(redirect_err)
        skip_logger_list = ["JEditor", "FrontEngine", "AutomationIDE"]
        for name in logging.root.manager.loggerDict.keys():
            if name in skip_logger_list:
                continue
            else:
                logging.getLogger(name).addHandler(redirect_err)

    @staticmethod
    def restore_std() -> None:
        """
        reset redirect
        :return: None
        """
        front_engine_logger.info("RedirectManager restore_std")
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__


redirect_manager_instance = RedirectManager()
