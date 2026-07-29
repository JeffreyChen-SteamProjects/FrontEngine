class FrontEngineException(Exception):
    pass


class FrontEngineOpenFileException(Exception):
    pass


class FrontEngineSaveFileException(Exception):
    pass


class FrontEngineJsonFileException(OSError):
    """
    設定檔／預設集讀寫失敗。繼承 OSError 是刻意的：所有呼叫端都寫
    `except (OSError, ValueError)`，若只繼承 Exception，那些處理器一個也不會
    生效——原本該顯示的警告訊息框不會出現，例外會一路炸穿到啟動流程。
    A settings/preset file could not be read or written. Inheriting OSError is
    deliberate: every call site guards `except (OSError, ValueError)`, and with a
    plain Exception base not one of those handlers ever fired - the warning
    dialogs never appeared and the exception escaped all the way to startup.
    """


class FrontEngineLoadUIException(Exception):
    pass
