from pathlib import Path
from typing import List

from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QMessageBox

from frontengine.ui.dialog.choose_file_dialog import choose_scene_json
from frontengine.ui.dialog.save_file_dialog import choose_file_get_save_filename
from frontengine.utils.json.json_file import write_json, read_json
from frontengine.utils.multi_language.language_wrapper import language_wrapper

tableview_model = QStandardItemModel()

# Set horizontal label
label_list = [
    language_wrapper.language_word_dict.get("scene_table_view_type"),
    language_wrapper.language_word_dict.get("scene_file_path"),
    language_wrapper.language_word_dict.get("url"),
    language_wrapper.language_word_dict.get("text"),
    language_wrapper.language_word_dict.get("Opacity"),
    language_wrapper.language_word_dict.get("Speed"),
    language_wrapper.language_word_dict.get("Volume"),
    language_wrapper.language_word_dict.get("Font size"),
    language_wrapper.language_word_dict.get("Play rate"),
    language_wrapper.language_word_dict.get("web_setting_open_local_file"),
    language_wrapper.language_word_dict.get("web_setting_open_enable_input"),
    language_wrapper.language_word_dict.get("position_x"),
    language_wrapper.language_word_dict.get("position_y"),
]
tableview_model.setHorizontalHeaderLabels(label_list)


def add_row_data(data_list: List):
    row = tableview_model.rowCount()
    for index, data in enumerate(data_list):
        tableview_model.setItem(row, index, QStandardItem(str(data)))


def output_scene_as_json(parent_qt_widget):
    output_dict = dict()
    output_setting = list()
    for row in range(tableview_model.rowCount()):
        settings = list()
        for column in range(tableview_model.columnCount()):
            settings.append(tableview_model.item(row, column).text())
        output_setting.append(settings)
    output_dict.update({"settings": output_setting})
    file_path = choose_file_get_save_filename(parent_qt_widget)
    if file_path is not None and file_path != "":
        file_path = Path(file_path)
        file_path = file_path.with_suffix(".json")
        write_json(str(file_path), output_dict)
    else:
        choose_path_to_output_message_box = QMessageBox(parent_qt_widget)
        choose_path_to_output_message_box.setText(
            language_wrapper.language_word_dict.get("scene_choose_output_path_message_box"))


def load_scene_json(parent_qt_widget):
    scene_file = choose_scene_json(parent_qt_widget)
    if scene_file is not None:
        scene_setting: dict = read_json(scene_file)
        scene_setting = scene_setting.get("settings")
        for setting in scene_setting:
            add_row_data(setting)
