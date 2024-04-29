import _thread
import sys

from PySide6.QtWidgets import QApplication
from je_auto_control import CriticalExit
from je_auto_control.wrapper.platform_wrapper import keyboard_check


class FrontEngineCriticalExit(CriticalExit):

    def run(self) -> None:
        """
        listener keycode _exit_check_key to interrupt
        """
        try:
            while True:
                if keyboard_check.check_key_is_press(self._exit_check_key):
                    _thread.interrupt_main()
                    QApplication.exit(0)
        except Exception as error:
            print(repr(error), file=sys.stderr)
