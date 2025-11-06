import sys
import json
from json import dumps, loads

from frontengine.utils.exception.exception_tags import cant_reformat_json_error, wrong_json_data_error
from frontengine.utils.exception.exceptions import FrontEngineJsonFileException


def _process_json(json_string: str, **kwargs) -> str:
    """
    嘗試將 JSON 字串重新格式化
    Try to reformat JSON string

    :param json_string: 原始 JSON 字串 (Original JSON string)
    :param kwargs: 傳遞給 json.dumps 的額外參數 (Extra arguments for json.dumps)
    :return: 格式化後的 JSON 字串 (Formatted JSON string)
    :raises FrontEngineJsonFileException: 當 JSON 無效或格式化失敗時拋出
    """
    try:
        parsed = loads(json_string)
        return dumps(parsed, indent=4, sort_keys=True, **kwargs)
    except json.JSONDecodeError as error:
        print(wrong_json_data_error, file=sys.stderr)
        raise FrontEngineJsonFileException(f"{wrong_json_data_error}: {error}")
    except Exception as error:
        raise FrontEngineJsonFileException(f"{wrong_json_data_error}: {error}")


def reformat_json(json_string: str, **kwargs) -> str:
    """
    將 JSON 字串重新格式化，並處理例外
    Reformat JSON string and handle exceptions

    :param json_string: 原始 JSON 字串 (Original JSON string)
    :param kwargs: 傳遞給 json.dumps 的額外參數 (Extra arguments for json.dumps)
    :return: 格式化後的 JSON 字串 (Formatted JSON string)
    :raises FrontEngineJsonFileException: 當重新格式化失敗時拋出
    """
    try:
        return _process_json(json_string, **kwargs)
    except FrontEngineJsonFileException:
        raise FrontEngineJsonFileException(cant_reformat_json_error)