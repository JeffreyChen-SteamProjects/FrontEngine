import os
from typing import Any, Dict, Optional

from PySide6.QtWidgets import QFileDialog, QWidget

from frontengine.ui.dialog.choose_file_dialog import choose_file
from frontengine.utils.json.json_repository import JsonRepository
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper

scene_json: Dict[str, Any] = {}


def choose_scene_json(
    trigger_ui: QWidget,
    file_filter: str = "Json (*.json;)",
    extensions: Optional[list[str]] = None,
) -> Optional[str]:
    front_engine_logger.info("choose_scene_json")

    file_path = choose_file(
        trigger_ui=trigger_ui,
        file_filter=file_filter,
        extensions=extensions or [".json"],
        warning_message=language_wrapper.language_word_dict.get("scene_choose_message_box"),
    )

    if not file_path:
        return None

    JsonRepository(file_path).load_into(scene_json, replace=True)
    return file_path


def write_scene_file(parent_qt_instance: QWidget, file_filter: str = "Json (*.json;)") -> Optional[str]:
    file_path, _ = QFileDialog().getSaveFileName(
        parent=parent_qt_instance,
        dir=os.getcwd(),
        filter=file_filter,
    )

    if not file_path:
        return None

    JsonRepository(file_path).save(scene_json)
    return file_path
