import ctypes
from typing import Union


def check_key_is_press(keycode: Union[int, str]) -> bool:
    """
    檢查指定的鍵是否被按下
    Check if the specified key is currently pressed

    :param keycode: 可以是整數虛擬鍵碼 (int) 或單一字元 (str)
                    Can be an integer virtual key code or a single character
    :return: True 如果按下，False 如果未按下
             True if pressed, False if not pressed
    """
    if isinstance(keycode, int):
        # 使用虛擬鍵碼檢查
        # Use virtual key code
        state: int = ctypes.windll.user32.GetAsyncKeyState(keycode)
    elif isinstance(keycode, str) and len(keycode) == 1:
        # 使用字元轉換成 ASCII，再檢查
        # Convert character to ASCII code and check
        state: int = ctypes.windll.user32.GetAsyncKeyState(ord(keycode))
    else:
        raise ValueError("keycode must be int (virtual key) or single-character str")

    # 根據 Win32 API 規則，返回值大於 1 表示按鍵被按下
    # According to Win32 API, return value > 1 means the key is pressed
    return state > 1