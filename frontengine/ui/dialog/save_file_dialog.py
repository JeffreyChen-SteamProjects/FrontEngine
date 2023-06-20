import os

from PySide6.QtWidgets import QFileDialog


def choose_file_get_save_filename(parent_qt_instance) -> str:
    """
    :param parent_qt_instance: Pyside parent
    :return: save code edit content to file
    """
    file_path = QFileDialog().getSaveFileName(
        parent=parent_qt_instance,
        dir=os.getcwd()
    )[0]
    return file_path
