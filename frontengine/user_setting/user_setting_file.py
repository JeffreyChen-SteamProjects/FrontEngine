from os import getcwd
from pathlib import Path
from typing import Any, Dict

from frontengine.utils.json.json_repository import JsonRepository

user_setting_dict: Dict[str, Any] = {
    "language": "English",
    "theme": "dark_amber.xml",
}


def _repository() -> JsonRepository:
    return JsonRepository(Path(getcwd()) / "user_setting.json")


def write_user_setting() -> Path:
    return _repository().save(user_setting_dict)


def read_user_setting() -> Path:
    repo = _repository()
    repo.load_into(user_setting_dict)
    return repo.path
