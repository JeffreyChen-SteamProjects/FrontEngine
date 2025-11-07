import os
from typing import Optional, Dict, Any

from PySide6.QtWidgets import QWidget, QFileDialog

from frontengine.ui.dialog.choose_file_dialog import choose_file
from frontengine.utils.json.json_file import write_json, read_json
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


# 全域場景設定資料
# Global scene configuration data
scene_json: Dict[str, Any] = {}


def choose_scene_json(
    trigger_ui: QWidget,
    file_filter: str = "Json (*.json;)",
    extensions: Optional[list[str]] = None
) -> Optional[str]:
    """
    開啟檔案選擇對話框，讀取場景 JSON 檔案並更新全域變數
    Open file dialog, read scene JSON file and update global variable

    :param trigger_ui: 觸發的父視窗 (Parent widget that triggers dialog)
    :param file_filter: 檔案過濾條件 (File filter string)
    :param extensions: 可接受的副檔名清單 (List of allowed extensions)
    :return: 選擇的檔案路徑 (Selected file path) 或 None
    """
    front_engine_logger.info("choose_scene_json")

    extensions = extensions or [".json"]

    file_path = choose_file(
        trigger_ui=trigger_ui,
        file_filter=file_filter,
        extensions=extensions,
        warning_message=language_wrapper.language_word_dict.get("scene_choose_message_box")
    )

    if file_path:
        # 更新全域場景設定
        # Update global scene configuration
        scene_json.update(read_json(file_path))
        return file_path

    return None


def write_scene_file(parent_qt_instance: QWidget, file_filter: str = "Json (*.json;)") -> Optional[str]:
    """
    開啟儲存檔案對話框，將場景設定寫入 JSON 檔案
    Open save file dialog, write scene configuration into JSON file

    :param parent_qt_instance: 父視窗 (Parent widget)
    :param file_filter: 檔案過濾條件 (File filter string)
    :return: 儲存的檔案路徑 (Saved file path) 或 None
    """
    file_path, _ = QFileDialog().getSaveFileName(
        parent=parent_qt_instance,
        dir=os.getcwd(),
        filter=file_filter
    )

    if file_path:
        write_json(file_path, scene_json)
        return file_path

    return None