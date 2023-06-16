import shutil
from pathlib import Path
from typing import Union

from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton, QTableView, QHeaderView, QScrollArea, QFileDialog, \
    QMessageBox

from frontengine.show.scene.scene import SceneManager
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class SceneSettingUI(QWidget):

    def __init__(self):
        super().__init__()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        # Init variable
        self.scene: Union[None, SceneManager] = None
        # Tableview
        self.scene_table_view = QTableView()
        self.scene_table_view_scroll_area = QScrollArea()
        self.scene_table_view_scroll_area.setWidgetResizable(True)
        self.scene_table_view_scroll_area.setViewportMargins(0, 0, 0, 0)
        self.scene_table_view_scroll_area.setWidget(self.scene_table_view)
        # Set resize as content
        self.scene_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.scene_table_view.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        # Data model
        self.table_view_model = QStandardItemModel()
        # Set horizontal label
        self.table_view_model.setHorizontalHeaderLabels([
            language_wrapper.language_word_dict.get("scene_table_view_type"),
            language_wrapper.language_word_dict.get("scene_file_path"),
            language_wrapper.language_word_dict.get("Opacity"),
            language_wrapper.language_word_dict.get("Speed"),
            language_wrapper.language_word_dict.get("Volume"),
            language_wrapper.language_word_dict.get("Font size"),
            language_wrapper.language_word_dict.get("Play rate")
        ])
        # # Set data
        # self.table_view_model.setItem(0, 0, QStandardItem("123"))
        # # Get data
        # print(self.table_view_model.item(0, 0).text())
        print(self.table_view_model.rowCount())
        print(self.table_view_model.columnCount())
        self.scene_table_view.setModel(self.table_view_model)
        # Start button
        self.start_button = QPushButton(
            language_wrapper.language_word_dict.get("scene_setting_start_scene_button")
        )
        self.start_button.clicked.connect(self.start_scene)
        # Add to layout
        self.grid_layout.addWidget(self.start_button, 0, 0)
        self.grid_layout.addWidget(self.scene_table_view_scroll_area, 0, 1, 10, 10)
        self.setLayout(self.grid_layout)
        self.scene = SceneManager()

    def add_image(self):
        self.table_view_model.setItem(self.table_view_model.rowCount(), 0, QStandardItem("IMAGE"))

    def add_gif(self):
        self.table_view_model.setItem(self.table_view_model.rowCount(), 0, QStandardItem("GIF"))

    def add_sound(self):
        self.table_view_model.setItem(self.table_view_model.rowCount(), 0, QStandardItem("SOUND"))

    def add_text(self):
        self.table_view_model.setItem(self.table_view_model.rowCount(), 0, QStandardItem("TEXT"))

    def add_video(self):
        self.table_view_model.setItem(self.table_view_model.rowCount(), 0, QStandardItem("VIDEO"))

    def add_web(self):
        self.table_view_model.setItem(self.table_view_model.rowCount(), 0, QStandardItem("WEB"))

    def add_extend_ui_file(self):
        self.table_view_model.setItem(self.table_view_model.rowCount(), 0, QStandardItem("EXTEND_UI_FILE"))

    def add_extend_ui(self):
        self.table_view_model.setItem(self.table_view_model.rowCount(), 0, QStandardItem("EXTEND_UI"))

    def close_scene(self):
        self.scene.widget_list.clear()
        self.scene.graphic_view.close()

    def start_scene(self) -> None:
        self.scene.graphic_view.showMaximized()
