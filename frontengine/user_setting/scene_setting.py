import os

from PySide6.QtWidgets import QWidget, QFileDialog

from frontengine.ui.dialog.choose_file_dialog import choose_file
from frontengine.utils.json.json_file import write_json, read_json
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper

scene_json = {

}


def choose_scene_json(
        trigger_ui: QWidget, file_filter: str = "Json (*.json;)", extensions: list = None) -> str:
    front_engine_logger.info("choose_scene_json")
    extensions = extensions or [".json"]
    file_path = choose_file(
        trigger_ui=trigger_ui, file_filter=file_filter, extensions=extensions,
        warning_message=language_wrapper.language_word_dict.get("scene_choose_message_box"))
    if file_path:
        scene_json.update(read_json(file_path))


def write_scene_file(parent_qt_instance: QWidget, file_filter: str = "Json (*.json;)"):
    file_path = QFileDialog().getSaveFileName(
        parent=parent_qt_instance,
        dir=os.getcwd(),
        filter=file_filter
    )
    if file_path:
        file_path = file_path[0]
        write_json(str(file_path), scene_json)
