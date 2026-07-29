import sys
import time
from threading import Thread
from typing import Union

from PySide6.QtWidgets import QApplication

from frontengine.utils.critical_exit.check_key_is_press import check_key_is_press
from frontengine.utils.critical_exit.win32_vk import keyboard_keys_table
from frontengine.utils.logging.loggin_instance import front_engine_logger


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
            resolved = keyboard_keys_table.get(keycode.lower())
            if resolved is None:
                # 認不得的鍵名以前會被存成 None，接著 check_key_is_press(None)
                # 丟出 ValueError，監聽執行緒當場結束——緊急退出鍵就這樣無聲失效。
                # An unknown key name used to be stored as None, after which
                # check_key_is_press(None) raised ValueError and killed the
                # listener thread: the emergency exit silently stopped working.
                raise ValueError(f"unknown key name: {keycode}")
            self._exit_check_key = resolved
        else:
            raise ValueError("keycode must be int or str")

    @staticmethod
    def available() -> bool:
        """
        這個平台支援不支援。check_key_is_press 走的是 Win32 的 GetAsyncKeyState，
        別的平台上只會丟 AttributeError。
        Whether this platform supports it: check_key_is_press goes through Win32's
        GetAsyncKeyState and raises AttributeError anywhere else.
        """
        return sys.platform == "win32"

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
        except SystemExit:
            raise
        except Exception as error:
            # 用 logger，不要 print 到 stderr：stderr 已經被 RedirectManager 換成
            # 佇列了，訊息會消失在沒人看的地方。這裡失效等於全螢幕覆蓋層的緊急
            # 出口不見了，是必須留下紀錄的事。
            # Log it rather than printing to stderr, which RedirectManager has
            # already replaced with a queue nobody reads. Losing this listener
            # means a fullscreen overlay has no emergency exit, which is worth a
            # record.
            front_engine_logger.error(f"[CriticalExit] listener stopped: {error!r}")

    def init_critical_exit(self) -> None:
        """
        啟動致命退出監聽器（平台不支援就不啟動）
        Start the critical exit listener, unless the platform cannot support it.
        """
        if not self.available():
            front_engine_logger.info(
                f"[CriticalExit] not supported on {sys.platform}, listener not started")
            return
        self.start()