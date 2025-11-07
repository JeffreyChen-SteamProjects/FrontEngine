import sys
import time
from threading import Thread
from typing import Union

from PySide6.QtWidgets import QApplication

from frontengine.utils.critical_exit.check_key_is_press import check_key_is_press
from frontengine.utils.critical_exit.win32_vk import keyboard_keys_table


class CriticalExit(Thread):
    """
    致命退出監聽器：在背景執行緒中監聽指定按鍵，按下後立即退出程式
    Critical Exit Listener: Runs in a background thread, listens for a key press, and exits the app immediately
    """

    def __init__(self, default_daemon: bool = True):
        """
        初始化 CriticalExit，預設監聽 F12 鍵
        Initialize CriticalExit, default key is F12

        :param default_daemon: 是否將執行緒設為 daemon (Whether to set thread as daemon)
        """
        super().__init__()
        self.daemon = default_daemon
        # 預設退出鍵為 F7
        # Default exit key is F7
        self._exit_check_key: int = keyboard_keys_table.get("f12")

    def set_critical_key(self, keycode: Union[int, str] = None) -> None:
        """
        設定退出按鍵
        Set the critical exit key

        :param keycode: 可以是虛擬鍵碼 (int) 或鍵盤名稱 (str)
                        Can be a virtual key code (int) or key name (str)
        """
        if isinstance(keycode, int):
            self._exit_check_key = keycode
        elif isinstance(keycode, str):
            self._exit_check_key = keyboard_keys_table.get(keycode)
        else:
            raise ValueError("keycode must be int or str")

    def run(self) -> None:
        """
        執行緒主迴圈：持續監聽指定按鍵，按下後結束應用程式
        Thread main loop: Continuously listens for the key, exits app when pressed
        """
        try:
            while True:
                time.sleep(0.1)
                if check_key_is_press(self._exit_check_key):
                    QApplication.exit(0)
                    sys.exit(0)
        except Exception as error:
            print(repr(error), file=sys.stderr)

    def init_critical_exit(self) -> None:
        """
        啟動致命退出監聽器
        Start the critical exit listener
        """
        self.start()