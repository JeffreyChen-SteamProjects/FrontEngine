import _thread
import sys
from threading import Thread

from PySide6.QtWidgets import QApplication

from frontengine.utils.critical_exit.check_key_is_press import check_key_is_press
from frontengine.utils.critical_exit.win32_vk import keyboard_keys_table


class CriticalExit(Thread):
    """
    use to make program interrupt
    """

    def __init__(self, default_daemon: bool = True):
        """
        default interrupt is keyboard F7 key
        :param default_daemon bool thread setDaemon
        """
        super().__init__()
        self.daemon = default_daemon
        self._exit_check_key: int = keyboard_keys_table.get("f7")

    def set_critical_key(self, keycode: [int, str] = None) -> None:
        """
        set interrupt key
        :param keycode interrupt key
        """
        if isinstance(keycode, int):
            self._exit_check_key = keycode
        else:
            self._exit_check_key = keyboard_keys_table.get(keycode)

    def run(self) -> None:
        """
        listener keycode _exit_check_key to interrupt
        """
        try:
            while True:
                if check_key_is_press(self._exit_check_key):
                    QApplication.exit(0)
        except Exception as error:
            print(repr(error), file=sys.stderr)

    def init_critical_exit(self) -> None:
        """
        should only use this to start critical exit
        may this function will add more
        """
        critical_thread = self
        critical_thread.start()
