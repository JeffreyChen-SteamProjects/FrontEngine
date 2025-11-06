from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QFileDialog, QWidget

from frontengine.utils.logging.loggin_instance import front_engine_logger


def choose_file_get_save_filename(parent_qt_instance: QWidget) -> Optional[str]:
    """
    開啟「另存新檔」對話框並回傳檔案路徑
    Open a "Save File" dialog and return the selected file path

    :param parent_qt_instance: PySide 親元件 / PySide parent widget
    :return: 檔案路徑或 None / File path or None
    """
    front_engine_logger.info(
        f"[SaveFileDialog] choose_file_get_save_filename | parent={parent_qt_instance}"
    )

    file_path, _ = QFileDialog.getSaveFileName(
        parent=parent_qt_instance,
        dir=str(Path.cwd())
    )

    return file_path if file_path else None
