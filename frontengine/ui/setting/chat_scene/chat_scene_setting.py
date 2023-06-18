from typing import Union, Dict, Callable

from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QWidget, QGridLayout, QTableView, QScrollArea, QHeaderView

from frontengine.show.scene.scene import SceneManager
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class Chat_Scene_UI(QWidget):

    def __init__(self):
        super().__init__()
        self.grid_layout = QGridLayout()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.scene: Union[None, SceneManager] = None
        self.scene = SceneManager()
        self.scene_component: Dict[str, Callable] = {
            "IMAGE": self.scene.add_image,
            "GIF": self.scene.add_gif,
            "SOUND": self.scene.add_sound,
            "TEXT": self.scene.add_text,
            "VIDEO": self.scene.add_video,
            "WEB": self.scene.add_web,
            "EXTEND_UI_FILE": self.scene.add_extend_ui_file
        }
        # Tableview
        self.scene_table_view = QTableView()
        self.scene_table_view_scroll_area = QScrollArea()
        self.scene_table_view_scroll_area.setWidgetResizable(True)
        self.scene_table_view_scroll_area.setViewportMargins(0, 0, 0, 0)
        self.scene_table_view_scroll_area.setWidget(self.scene_table_view)
        # Data model
        self.table_view_model = QStandardItemModel()
        # Set horizontal label
        self.label_list = [
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
        self.param_key_name_list = [
            "widget_type", "file_path", "url", "text", "opacity", "speed", "volume", "font_size", "play_rate",
            "web_setting_open_local_file", "web_setting_open_enable_input", "position_x", "position_y"
        ]
        self.table_view_model.setHorizontalHeaderLabels(self.label_list)
        # Set resize as content
        self.scene_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.scene_table_view.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.scene_table_view.setModel(self.table_view_model)

    def start_scene(self) -> None:
        front_engine_logger.info("start_scene")
        for row in range(self.table_view_model.rowCount()):
            widget_type_text = self.table_view_model.item(row, 0).text()
            add_widget_function = self.scene_component.get(widget_type_text)
            param_dict: Dict[str, str] = dict()
            for column in range(1, self.table_view_model.columnCount()):
                param = self.table_view_model.item(row, column).text()
                if param != "":
                    param_dict.update({self.param_key_name_list[column]: param})
            add_widget_function(param_dict)
            front_engine_logger.info(f"start_scene type: {widget_type_text}, param: {param_dict}")
        self.scene.show()
