from os import getcwd
from pathlib import Path
from typing import Dict, Any

from frontengine.utils.json.json_file import read_json, write_json

# 使用者設定的全域字典
# Global dictionary for user settings
user_setting_dict: Dict[str, Any] = {
    "language": "English",
    "theme": "dark_amber.xml",
}


def write_user_setting() -> Path:
    """
    將使用者設定寫入 JSON 檔案
    Write user settings into JSON file

    :return: 設定檔路徑 (Path to the settings file)
    """
    user_setting_file = Path(getcwd()) / "user_setting.json"
    write_json(str(user_setting_file), user_setting_dict)
    return user_setting_file


def read_user_setting() -> Path:
    """
    讀取使用者設定檔，並更新全域字典
    Read user settings from JSON file and update global dictionary

    :return: 設定檔路徑 (Path to the settings file)
    """
    user_setting_file = Path(getcwd()) / "user_setting.json"
    if user_setting_file.exists() and user_setting_file.is_file():
        user_setting_dict.update(read_json(str(user_setting_file)))
    return user_setting_file