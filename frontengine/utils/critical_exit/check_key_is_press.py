import ctypes
from typing import Union

def check_key_is_press(keycode: Union[int, str]) -> bool:
    """
    檢查指定的鍵是否被按下 (Windows only)
    Check if the specified key is currently pressed
    """
    if isinstance(keycode, int):
        # 使用虛擬鍵碼檢查
        state: int = ctypes.windll.user32.GetAsyncKeyState(keycode)
    elif isinstance(keycode, str) and len(keycode) == 1:
        # 使用字元轉換成 ASCII，再檢查
        state: int = ctypes.windll.user32.GetAsyncKeyState(ord(keycode.upper()))
    else:
        raise ValueError("keycode must be int (virtual key) or single-character str")

    # 判斷最高位元是否為 1 → 表示按鍵正在被按下
    return (state & 0x8000) != 0
