from typing import Union

from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton, QTableView, QHeaderView, QScrollArea, QLineEdit

from frontengine.show.load.load_someone_make_ui import load_ui_file
from frontengine.show.scene.scene import SceneManager
from frontengine.ui.setting.choose_dialog.choose_file_dialog import choose_video, choose_player_sound, choose_gif, \
    choose_image
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
        # Data model
        self.table_view_model = QStandardItemModel()
        # Set horizontal label
        self.table_view_model.setHorizontalHeaderLabels([
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
        ])
        # Set resize as content
        self.scene_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.scene_table_view.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        # # Get data
        # print(self.table_view_model.item(0, 0).text())
        self.scene_table_view.setModel(self.table_view_model)
        # Image button
        self.image_button = QPushButton(
            language_wrapper.language_word_dict.get("scene_add_image")
        )
        self.image_button.clicked.connect(self.add_image)
        # GIF button
        self.gif_button = QPushButton(
            language_wrapper.language_word_dict.get("scene_add_gif")
        )
        self.gif_button.clicked.connect(self.add_gif)
        # SOUND button
        self.sound_button = QPushButton(
            language_wrapper.language_word_dict.get("scene_add_sound")
        )
        self.sound_button.clicked.connect(self.add_sound)
        # Text button
        self.text_input = QLineEdit()
        self.text_input.setText(
            language_wrapper.language_word_dict.get("text")
        )
        self.text_button = QPushButton(
            language_wrapper.language_word_dict.get("scene_add_text")
        )
        self.text_button.clicked.connect(self.add_sound)
        # Video button
        self.video_button = QPushButton(
            language_wrapper.language_word_dict.get("scene_add_video")
        )
        self.video_button.clicked.connect(self.add_sound)
        # Web button
        self.web_button = QPushButton(
            language_wrapper.language_word_dict.get("scene_add_web")
        )
        self.web_url_input = QLineEdit()
        self.web_url_input.setText(
            language_wrapper.language_word_dict.get("url")
        )
        self.web_button.clicked.connect(self.add_sound)
        # UI button
        self.ui_button = QPushButton(
            language_wrapper.language_word_dict.get("scene_add_UI")
        )
        self.ui_path_input = QLineEdit()
        self.ui_path_input.setText(
            language_wrapper.language_word_dict.get("ui_path")
        )
        self.ui_button.clicked.connect(self.add_sound)
        # Start button
        self.start_button = QPushButton(
            language_wrapper.language_word_dict.get("scene_setting_start_scene_button")
        )
        self.start_button.clicked.connect(self.start_scene)
        # Add to layout
        self.grid_layout.addWidget(self.image_button, 0, 0)
        self.grid_layout.addWidget(self.gif_button, 0, 1)
        self.grid_layout.addWidget(self.sound_button, 0, 2)
        self.grid_layout.addWidget(self.text_button, 0, 3)
        self.grid_layout.addWidget(self.text_input, 1, 3)
        self.grid_layout.addWidget(self.video_button, 0, 4)
        self.grid_layout.addWidget(self.web_url_input, 1, 1)
        self.grid_layout.addWidget(self.web_button, 0, 5)
        self.grid_layout.addWidget(self.ui_path_input, 1, 5)
        self.grid_layout.addWidget(self.ui_button, 0, 6)
        self.grid_layout.addWidget(self.start_button, 0, 7)
        self.grid_layout.addWidget(self.scene_table_view_scroll_area, 2, 0, 10, 10)
        self.setLayout(self.grid_layout)
        self.scene = SceneManager()
        # Use to build component
        self.scene_component = {
            "IMAGE": self.scene.add_image,
            "GIF": self.scene.add_gif,
            "SOUND": self.scene.add_sound,
            "TEXT": self.scene.add_text,
            "VIDEO": self.scene.add_video,
            "WEB": self.scene.add_web,
            "EXTEND_UI_FILE": self.scene.add_extend_ui_file
        }

    def add_image(self):
        image_path = choose_image(self)
        if image_path is not None:
            row = self.table_view_model.rowCount()
            self.table_view_model.setItem(row, 0, QStandardItem("IMAGE"))
            self.table_view_model.setItem(row, 1, QStandardItem(image_path))
            self.table_view_model.setItem(row, 2, QStandardItem(""))
            self.table_view_model.setItem(row, 3, QStandardItem(""))
            self.table_view_model.setItem(row, 4, QStandardItem(""))
            self.table_view_model.setItem(row, 5, QStandardItem(""))
            self.table_view_model.setItem(row, 6, QStandardItem(""))
            self.table_view_model.setItem(row, 7, QStandardItem(""))
            self.table_view_model.setItem(row, 8, QStandardItem(""))

    def add_gif(self):
        gif_path = choose_gif(self)
        if gif_path is not None:
            row = self.table_view_model.rowCount()
            self.table_view_model.setItem(row, 0, QStandardItem("GIF"))
            self.table_view_model.setItem(row, 1, QStandardItem(gif_path))
            self.table_view_model.setItem(row, 2, QStandardItem(""))
            self.table_view_model.setItem(row, 3, QStandardItem(""))
            self.table_view_model.setItem(row, 4, QStandardItem(""))
            self.table_view_model.setItem(row, 5, QStandardItem(""))
            self.table_view_model.setItem(row, 6, QStandardItem(""))
            self.table_view_model.setItem(row, 7, QStandardItem(""))
            self.table_view_model.setItem(row, 8, QStandardItem(""))

    def add_sound(self):
        sound_path = choose_player_sound(self)
        if sound_path is not None:
            row = self.table_view_model.rowCount()
            self.table_view_model.setItem(row, 0, QStandardItem("SOUND"))
            self.table_view_model.setItem(row, 1, QStandardItem(sound_path))
            self.table_view_model.setItem(row, 2, QStandardItem(""))
            self.table_view_model.setItem(row, 3, QStandardItem(""))
            self.table_view_model.setItem(row, 4, QStandardItem(""))
            self.table_view_model.setItem(row, 5, QStandardItem(""))
            self.table_view_model.setItem(row, 6, QStandardItem(""))
            self.table_view_model.setItem(row, 7, QStandardItem(""))
            self.table_view_model.setItem(row, 8, QStandardItem(""))

    def add_text(self):
        row = self.table_view_model.rowCount()
        self.table_view_model.setItem(row, 0, QStandardItem("TEXT"))
        self.table_view_model.setItem(row, 1, QStandardItem(""))
        self.table_view_model.setItem(row, 2, QStandardItem(""))
        self.table_view_model.setItem(row, 3, QStandardItem(""))
        self.table_view_model.setItem(row, 4, QStandardItem(""))
        self.table_view_model.setItem(row, 5, QStandardItem(""))
        self.table_view_model.setItem(row, 6, QStandardItem(""))
        self.table_view_model.setItem(row, 7, QStandardItem(""))
        self.table_view_model.setItem(row, 8, QStandardItem(""))

    def add_video(self):
        video_path = choose_video(self)
        if video_path is not None:
            row = self.table_view_model.rowCount()
            self.table_view_model.setItem(row, 0, QStandardItem("VIDEO"))
            self.table_view_model.setItem(row, 1, QStandardItem(video_path))
            self.table_view_model.setItem(row, 2, QStandardItem(""))
            self.table_view_model.setItem(row, 3, QStandardItem(""))
            self.table_view_model.setItem(row, 4, QStandardItem(""))
            self.table_view_model.setItem(row, 5, QStandardItem(""))
            self.table_view_model.setItem(row, 6, QStandardItem(""))
            self.table_view_model.setItem(row, 7, QStandardItem(""))
            self.table_view_model.setItem(row, 8, QStandardItem(""))

    def add_web(self):
        row = self.table_view_model.rowCount()
        self.table_view_model.setItem(row, 0, QStandardItem("WEB"))
        self.table_view_model.setItem(row, 1, QStandardItem(""))
        self.table_view_model.setItem(row, 2, QStandardItem(self.web_url_input.text()))
        self.table_view_model.setItem(row, 3, QStandardItem(""))
        self.table_view_model.setItem(row, 4, QStandardItem(""))
        self.table_view_model.setItem(row, 5, QStandardItem(""))
        self.table_view_model.setItem(row, 6, QStandardItem(""))
        self.table_view_model.setItem(row, 7, QStandardItem(""))
        self.table_view_model.setItem(row, 8, QStandardItem(""))

    def add_extend_ui_file(self):
        if load_ui_file(self.ui_path_input.text()):
            row = self.table_view_model.rowCount()
            self.table_view_model.setItem(row, 0, QStandardItem("EXTEND_UI_FILE"))
            self.table_view_model.setItem(row, 1, QStandardItem(self.ui_path_input.text()))
            self.table_view_model.setItem(row, 2, QStandardItem(""))
            self.table_view_model.setItem(row, 3, QStandardItem(""))
            self.table_view_model.setItem(row, 4, QStandardItem(""))
            self.table_view_model.setItem(row, 5, QStandardItem(""))
            self.table_view_model.setItem(row, 6, QStandardItem(""))
            self.table_view_model.setItem(row, 7, QStandardItem(""))
            self.table_view_model.setItem(row, 8, QStandardItem(""))

    def close_scene(self):
        self.scene.widget_list.clear()
        self.scene.graphic_view.close()

    def start_scene(self) -> None:
        self.scene.graphic_view.showMaximized()
