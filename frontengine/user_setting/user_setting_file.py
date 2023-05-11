from os import getcwd
from pathlib import Path

from frontengine.utils.json.json_file import read_json
from frontengine.utils.json.json_file import write_json

user_setting_dict = {
    "language": "English"
}


def write_user_setting():
    user_setting_file = Path(getcwd() + "/user_setting.json")
    write_json(str(user_setting_file), user_setting_dict)


def read_user_setting():
    user_setting_file = Path(getcwd() + "/user_setting.json")
    if user_setting_file.exists() and user_setting_file.is_file():
        user_setting_dict.update(read_json(str(user_setting_file)))
