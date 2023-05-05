from pathlib import Path
from threading import Lock

from frontengine.utils.exception.exceptions import FrontEngineOpenFileException


def read_file(file):
    """
    use to check file is exist and open
    :param file: the file we want to read its whole file path
    :return: read's file and file content
    try
        lock thread
        find file is exist ? and is file ?
        if both is true
            try to open it and read
            return file and content
    finally
        release lock
    """
    lock = Lock()
    try:
        lock.acquire()
        if file != "" and file is not None:
            file_path = Path(file)
            if file_path.exists() and file_path.is_file():
                with open(file, "r+") as open_read_file:
                    return [file, open_read_file.read()]
    except FrontEngineOpenFileException:
        raise FrontEngineOpenFileException
    finally:
        lock.release()



