from typing import Union

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIntValidator
from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton, QTableView, QHeaderView, QScrollArea, QLineEdit, \
    QSlider, QLabel, QCheckBox, QMessageBox

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
            language_wrapper.language_word_dict.get("position_x"),
            language_wrapper.language_word_dict.get("position_y"),
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
        self.text_button.clicked.connect(self.add_text)
        # Video button
        self.video_button = QPushButton(
            language_wrapper.language_word_dict.get("scene_add_video")
        )
        self.video_button.clicked.connect(self.add_video)
        # Web button
        self.web_button = QPushButton(
            language_wrapper.language_word_dict.get("scene_add_web")
        )
        self.web_url_input = QLineEdit()
        self.web_url_input.setText(
            language_wrapper.language_word_dict.get("url")
        )
        self.web_button.clicked.connect(self.add_web)
        # UI button
        self.ui_button = QPushButton(
            language_wrapper.language_word_dict.get("scene_add_UI")
        )
        self.ui_path_input = QLineEdit()
        self.ui_path_input.setText(
            language_wrapper.language_word_dict.get("ui_path")
        )
        self.ui_button.clicked.connect(self.add_extend_ui_file)
        # Start button
        self.start_button = QPushButton(
            language_wrapper.language_word_dict.get("scene_setting_start_scene_button")
        )
        self.start_button.clicked.connect(self.start_scene)
        # Opacity slider
        self.opacity_slider = QSlider()
        self.opacity_slider.setMinimum(1)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setTickInterval(1)
        self.opacity_slider.setValue(20)
        self.opacity_slider.setOrientation(Qt.Orientation.Horizontal)
        self.opacity_label = QLabel()
        self.opacity_label.setText(language_wrapper.language_word_dict.get("Opacity"))
        # Speed slider
        self.speed_slider = QSlider()
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(100)
        self.speed_slider.setTickInterval(1)
        self.speed_slider.setValue(100)
        self.speed_slider.setOrientation(Qt.Orientation.Horizontal)
        self.speed_label = QLabel()
        self.speed_label.setText(language_wrapper.language_word_dict.get("Speed"))
        # Volume slider
        self.volume_slider = QSlider()
        self.volume_slider.setMinimum(1)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setTickInterval(1)
        self.volume_slider.setValue(100)
        self.volume_slider.setOrientation(Qt.Orientation.Horizontal)
        self.volume_label = QLabel()
        self.volume_label.setText(language_wrapper.language_word_dict.get("Volume"))
        # Font size slider
        self.font_size_slider = QSlider()
        self.font_size_slider = QSlider()
        self.font_size_slider.setMinimum(1)
        self.font_size_slider.setMaximum(100)
        self.font_size_slider.setTickInterval(1)
        self.font_size_slider.setValue(100)
        self.font_size_slider.setOrientation(Qt.Orientation.Horizontal)
        self.front_size_label = QLabel()
        self.front_size_label.setText(language_wrapper.language_word_dict.get("Font size"))
        # Play rate slider
        self.play_rate_slider = QSlider()
        self.play_rate_slider.setMinimum(1)
        self.play_rate_slider.setMaximum(100)
        self.play_rate_slider.setTickInterval(1)
        self.play_rate_slider.setValue(100)
        self.play_rate_slider.setOrientation(Qt.Orientation.Horizontal)
        self.play_rate_label = QLabel()
        self.play_rate_label.setText(language_wrapper.language_word_dict.get("Play rate"))
        # Checkbox
        self.enable_web_input_checkbox = QCheckBox(
            language_wrapper.language_word_dict.get("web_setting_open_enable_input"))
        self.enable_web_local_file_checkbox = QCheckBox(
            language_wrapper.language_word_dict.get("web_setting_open_local_file"))
        # Position x, y input
        self.position_x_input_label = QLabel(language_wrapper.language_word_dict.get("position_x"))
        self.position_x_input = QLineEdit()
        self.position_x_input.setValidator(QIntValidator(0, 999999, self))
        self.position_y_input_label = QLabel(language_wrapper.language_word_dict.get("position_y"))
        self.position_y_input = QLineEdit()
        self.position_y_input.setValidator(QIntValidator(0, 999999, self))
        # Add to layout
        self.grid_layout.addWidget(self.image_button, 0, 0)
        self.grid_layout.addWidget(self.text_input, 0, 1, 1, 200)
        self.grid_layout.addWidget(self.gif_button, 1, 0)
        self.grid_layout.addWidget(self.web_url_input, 1, 1, 1, 200)
        self.grid_layout.addWidget(self.sound_button, 2, 0)
        self.grid_layout.addWidget(self.ui_path_input, 2, 1, 1, 200)
        self.grid_layout.addWidget(self.text_button, 3, 0)
        self.grid_layout.addWidget(self.opacity_label, 3, 1)
        self.grid_layout.addWidget(self.opacity_slider, 3, 2, 0, 200)
        self.grid_layout.addWidget(self.video_button, 4, 0)
        self.grid_layout.addWidget(self.speed_label, 4, 1)
        self.grid_layout.addWidget(self.speed_slider, 4, 2, 0, 200)
        self.grid_layout.addWidget(self.web_button, 5, 0)
        self.grid_layout.addWidget(self.volume_label, 5, 1)
        self.grid_layout.addWidget(self.volume_slider, 5, 2, 0, 200)
        self.grid_layout.addWidget(self.ui_button, 6, 0)
        self.grid_layout.addWidget(self.front_size_label, 6, 1)
        self.grid_layout.addWidget(self.font_size_slider, 6, 2, 0, 200)
        self.grid_layout.addWidget(self.start_button, 7, 0)
        self.grid_layout.addWidget(self.play_rate_label, 7, 1)
        self.grid_layout.addWidget(self.play_rate_slider, 7, 2, 0, 200)
        self.grid_layout.addWidget(self.enable_web_input_checkbox, 8, 0)
        self.grid_layout.addWidget(self.enable_web_local_file_checkbox, 8, 1)
        self.grid_layout.addWidget(self.position_x_input_label, 9, 0)
        self.grid_layout.addWidget(self.position_x_input, 9, 1)
        self.grid_layout.addWidget(self.position_y_input_label, 10, 0)
        self.grid_layout.addWidget(self.position_y_input, 10, 1)
        self.grid_layout.addWidget(self.scene_table_view_scroll_area, 11, 0, 70, 200)
        self.scroll_area = QScrollArea()
        self.scroll_area.setLayout(self.grid_layout)
        self.setLayout(self.scroll_area.layout())
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
            self.table_view_model.setItem(row, 4, QStandardItem(str(self.opacity_slider.value())))
            self.table_view_model.setItem(row, 5, QStandardItem(""))
            self.table_view_model.setItem(row, 6, QStandardItem(""))
            self.table_view_model.setItem(row, 7, QStandardItem(""))
            self.table_view_model.setItem(row, 8, QStandardItem(""))
            self.table_view_model.setItem(row, 9, QStandardItem(""))
            self.table_view_model.setItem(row, 10, QStandardItem(""))
            self.table_view_model.setItem(row, 11, QStandardItem(self.position_x_input.text()))
            self.table_view_model.setItem(row, 12, QStandardItem(self.position_y_input.text()))

    def add_gif(self):
        gif_path = choose_gif(self)
        if gif_path is not None:
            row = self.table_view_model.rowCount()
            self.table_view_model.setItem(row, 0, QStandardItem("GIF"))
            self.table_view_model.setItem(row, 1, QStandardItem(gif_path))
            self.table_view_model.setItem(row, 2, QStandardItem(""))
            self.table_view_model.setItem(row, 3, QStandardItem(""))
            self.table_view_model.setItem(row, 4, QStandardItem(str(self.opacity_slider.value())))
            self.table_view_model.setItem(row, 5, QStandardItem(str(self.speed_slider.value())))
            self.table_view_model.setItem(row, 6, QStandardItem(""))
            self.table_view_model.setItem(row, 7, QStandardItem(""))
            self.table_view_model.setItem(row, 8, QStandardItem(""))
            self.table_view_model.setItem(row, 9, QStandardItem(""))
            self.table_view_model.setItem(row, 10, QStandardItem(""))
            self.table_view_model.setItem(row, 11, QStandardItem(self.position_x_input.text()))
            self.table_view_model.setItem(row, 12, QStandardItem(self.position_y_input.text()))

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
            self.table_view_model.setItem(row, 6, QStandardItem(str(self.volume_slider.value())))
            self.table_view_model.setItem(row, 7, QStandardItem(""))
            self.table_view_model.setItem(row, 8, QStandardItem(""))
            self.table_view_model.setItem(row, 9, QStandardItem(""))
            self.table_view_model.setItem(row, 10, QStandardItem(""))
            self.table_view_model.setItem(row, 11, QStandardItem(self.position_x_input.text()))
            self.table_view_model.setItem(row, 12, QStandardItem(self.position_y_input.text()))

    def add_text(self):
        row = self.table_view_model.rowCount()
        self.table_view_model.setItem(row, 0, QStandardItem("TEXT"))
        self.table_view_model.setItem(row, 1, QStandardItem(""))
        self.table_view_model.setItem(row, 2, QStandardItem(""))
        self.table_view_model.setItem(row, 3, QStandardItem(self.text_input.text()))
        self.table_view_model.setItem(row, 4, QStandardItem(str(self.opacity_slider.value())))
        self.table_view_model.setItem(row, 5, QStandardItem(""))
        self.table_view_model.setItem(row, 6, QStandardItem(""))
        self.table_view_model.setItem(row, 7, QStandardItem(str(self.font_size_slider.value())))
        self.table_view_model.setItem(row, 8, QStandardItem(""))
        self.table_view_model.setItem(row, 9, QStandardItem(""))
        self.table_view_model.setItem(row, 10, QStandardItem(""))
        self.table_view_model.setItem(row, 11, QStandardItem(self.position_x_input.text()))
        self.table_view_model.setItem(row, 12, QStandardItem(self.position_y_input.text()))

    def add_video(self):
        video_path = choose_video(self)
        if video_path is not None:
            row = self.table_view_model.rowCount()
            self.table_view_model.setItem(row, 0, QStandardItem("VIDEO"))
            self.table_view_model.setItem(row, 1, QStandardItem(video_path))
            self.table_view_model.setItem(row, 2, QStandardItem(""))
            self.table_view_model.setItem(row, 3, QStandardItem(""))
            self.table_view_model.setItem(row, 4, QStandardItem(str(self.opacity_slider.value())))
            self.table_view_model.setItem(row, 5, QStandardItem(""))
            self.table_view_model.setItem(row, 6, QStandardItem(str(self.volume_slider.value())))
            self.table_view_model.setItem(row, 7, QStandardItem(""))
            self.table_view_model.setItem(row, 8, QStandardItem(str(self.play_rate_slider.value())))
            self.table_view_model.setItem(row, 9, QStandardItem(""))
            self.table_view_model.setItem(row, 10, QStandardItem(""))
            self.table_view_model.setItem(row, 11, QStandardItem(self.position_x_input.text()))
            self.table_view_model.setItem(row, 12, QStandardItem(self.position_y_input.text()))

    def add_web(self):
        row = self.table_view_model.rowCount()
        self.table_view_model.setItem(row, 0, QStandardItem("WEB"))
        self.table_view_model.setItem(row, 1, QStandardItem(""))
        self.table_view_model.setItem(row, 2, QStandardItem(self.web_url_input.text()))
        self.table_view_model.setItem(row, 3, QStandardItem(""))
        self.table_view_model.setItem(row, 4, QStandardItem(str(self.opacity_slider.value())))
        self.table_view_model.setItem(row, 5, QStandardItem(""))
        self.table_view_model.setItem(row, 6, QStandardItem(""))
        self.table_view_model.setItem(row, 7, QStandardItem(""))
        self.table_view_model.setItem(row, 8, QStandardItem(""))
        self.table_view_model.setItem(row, 9, QStandardItem(""))
        self.table_view_model.setItem(row, 10, QStandardItem(""))
        self.table_view_model.setItem(row, 11, QStandardItem(self.position_x_input.text()))
        self.table_view_model.setItem(row, 12, QStandardItem(self.position_y_input.text()))

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
            self.table_view_model.setItem(row, 9, QStandardItem(""))
            self.table_view_model.setItem(row, 10, QStandardItem(""))
            self.table_view_model.setItem(row, 11, QStandardItem(self.position_x_input.text()))
            self.table_view_model.setItem(row, 12, QStandardItem(self.position_y_input.text()))

        else:
            ui_not_found_message = QMessageBox(self)
            ui_not_found_message.setText(
                language_wrapper.language_word_dict.get("cant_find_extend_ui_message_box_text"))
            ui_not_found_message.show()

    def close_scene(self):
        self.scene.widget_list.clear()
        self.scene.graphic_view.close()

    def start_scene(self) -> None:
        self.scene.graphic_view.showMaximized()
