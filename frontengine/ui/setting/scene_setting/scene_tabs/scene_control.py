from typing import Dict, Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton, QHeaderView, QTableView, QScrollArea

from frontengine.show.scene.scene import SceneManager
from frontengine.ui.setting.scene_setting.scene_tabs.tableview_model import tableview_model, output_scene_as_json, \
    load_scene_json
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class SceneControlSettingUI(QWidget):

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.grad_layout = QGridLayout()
        self.param_key_name_list = [
            "widget_type", "file_path", "url", "text", "opacity", "speed", "volume", "font_size", "play_rate",
            "web_setting_open_local_file", "web_setting_open_enable_input", "position_x", "position_y"
        ]
        # Use to build component
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
        # Set resize as content
        self.scene_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.scene_table_view.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.scene_table_view.setModel(tableview_model)
        # Scene output & input
        self.scene_output_button = QPushButton(language_wrapper.language_word_dict.get("scene_output"))
        self.scene_output_button.clicked.connect(output_scene_as_json)
        self.scene_input_button = QPushButton(language_wrapper.language_word_dict.get("scene_input"))
        self.scene_input_button.clicked.connect(load_scene_json)
        # Start button
        self.start_button = QPushButton(
            language_wrapper.language_word_dict.get("scene_setting_start_scene_button")
        )
        self.start_button.clicked.connect(self.start_scene)
        # Add to layout
        self.grad_layout.addWidget(self.scene_input_button, 0, 0)
        self.grad_layout.addWidget(self.scene_output_button, 0, 1)
        self.grad_layout.addWidget(self.start_button, 0, 2)
        self.grad_layout.addWidget(self.scene_table_view_scroll_area, 1, 0, -1, -1)
        self.setLayout(self.grad_layout)

    def close_scene(self) -> None:
        self.scene.widget_list.clear()
        if self.scene.graphic_view.isEnabled() and self.scene.graphic_view.isVisible():
            self.scene.graphic_view.close()

    def start_scene(self) -> None:
        front_engine_logger.info("start_scene")
        for row in range(tableview_model.rowCount()):
            widget_type_text = tableview_model.item(row, 0).text()
            add_widget_function = self.scene_component.get(widget_type_text)
            param_dict: Dict[str, str] = dict()
            for column in range(1, tableview_model.columnCount()):
                param = tableview_model.item(row, column).text()
                if param != "":
                    param_dict.update({self.param_key_name_list[column]: param})
            add_widget_function(param_dict)
            front_engine_logger.info(f"start_scene type: {widget_type_text}, param: {param_dict}")
        self.scene.show()
