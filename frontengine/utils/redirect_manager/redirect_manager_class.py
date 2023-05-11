import logging
import queue
import sys


class RedirectStdOut(logging.Handler):

    # redirect logging std output to queue

    def __init__(self):
        super().__init__()

    def write(self, content_to_write):
        redirect_manager_instance.std_out_queue.put(content_to_write)

    def emit(self, record: logging.LogRecord) -> None:
        redirect_manager_instance.std_out_queue.put(self.format(record))


class RedirectStdErr(logging.Handler):

    # redirect logging stderr output to queue

    def __init__(self):
        super().__init__()

    def write(self, content_to_write):
        redirect_manager_instance.std_err_queue.put(content_to_write)

    def emit(self, record: logging.LogRecord) -> None:
        redirect_manager_instance.std_err_queue.put(self.format(record))


class RedirectManager(object):

    def __init__(self):
        self.is_use_ui: bool = False
        self.ui = None
        self.std_err_queue = queue.Queue()
        self.std_out_queue = queue.Queue()

    def set_redirect(self, ui, is_use_ui: bool = False):
        """
        :param ui: tkinter_ui instance
        :param is_use_ui: false for cli
        :return: None
        """
        self.ui = ui
        self.is_use_ui = is_use_ui
        if self.is_use_ui is True and self.ui is not None:
            redirect_out = RedirectStdOut()
            redirect_err = RedirectStdErr()
            sys.stdout = redirect_out
            sys.stderr = redirect_err
            default_logger = logging.getLogger()
            default_logger.addHandler(redirect_err)
            for name in logging.root.manager.loggerDict.keys():
                logging.getLogger(name).addHandler(redirect_err)

    @staticmethod
    def restore_std():
        """
        reset redirect
        :return: None
        """
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__


redirect_manager_instance = RedirectManager()
