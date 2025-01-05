import os

from PySide6.QtWidgets import QFileDialog

from frontengine.utils.logging.loggin_instance import front_engine_logger


def choose_file_get_save_filename(parent_qt_instance) -> str:
    """
    :param parent_qt_instance: Pyside parent
    :return: save code edit content to file
    """
    front_engine_logger.info("save_file_dialog.py choose_file_get_save_filename "
                             f"parent_qt_instance: {parent_qt_instance}")
    file_path = QFileDialog().getSaveFileName(
        parent=parent_qt_instance,
        dir=os.getcwd()
    )[0]
    return file_path
