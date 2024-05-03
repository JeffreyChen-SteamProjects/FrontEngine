import ctypes


def check_key_is_press(keycode: [int, str]) -> bool:
    if isinstance(keycode, int):
        temp: int = ctypes.windll.user32.GetAsyncKeyState(keycode)
    else:
        temp = ctypes.windll.user32.GetAsyncKeyState(ord(keycode))
    if temp > 1:
        return True
    return False
