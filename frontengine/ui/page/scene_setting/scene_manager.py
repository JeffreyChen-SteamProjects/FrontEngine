import json

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget, QGridLayout, QPlainTextEdit, QPushButton, QCheckBox, QDialog

from frontengine.show.scene.extend_graphic_view import ExtendGraphicView
from frontengine.ui.page.utils import monitor_choose_dialog
from frontengine.user_setting.scene_setting import choose_scene_json, write_scene_file, scene_json
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class SceneManagerUI(QWidget):

    def __init__(self, scene_manager):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.grid_layout = QGridLayout()
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.scene = scene_manager
        self.show_all_screen = False
        # Read and write scene json button
        self.read_scene_json_button = QPushButton(language_wrapper.language_word_dict.get("scene_input"))
        self.read_scene_json_button.clicked.connect(self.update_scene_json)
        self.write_scene_json_button = QPushButton(language_wrapper.language_word_dict.get("scene_output"))
        self.write_scene_json_button.clicked.connect(lambda: write_scene_file(self))
        # Json plaintext
        self.json_plaintext = QPlainTextEdit()
        self.json_plaintext.setReadOnly(True)
        self.json_plaintext.appendPlainText("{}")
        # Start button
        self.start_button = QPushButton(
            language_wrapper.language_word_dict.get("scene_start")
        )
        self.start_button.clicked.connect(self.start_scene)
        # Show on all screen
        self.show_on_all_screen_checkbox = QCheckBox(
            language_wrapper.language_word_dict.get("Show on all screen")
        )
        self.show_on_all_screen_checkbox.clicked.connect(self.set_show_all_screen)
        # Add to layout
        self.grid_layout.addWidget(self.json_plaintext, 0, 0, -1, -1)
        self.grid_layout.addWidget(self.read_scene_json_button, 1, 0)
        self.grid_layout.addWidget(self.write_scene_json_button, 1, 1)
        self.grid_layout.addWidget(self.show_on_all_screen_checkbox, 2, 0)
        self.grid_layout.addWidget(self.start_button, 3, 0, 1, 0)
        self.setLayout(self.grid_layout)

    def set_show_all_screen(self) -> None:
        self.show_all_screen = self.show_on_all_screen_checkbox.isChecked()

    def start_scene(self):
        scene: dict = json.loads(self.json_plaintext.toPlainText())
        scene_add_function = {
            "TEXT": self.scene.add_text,
            "IMAGE": self.scene.add_image,
            "GIF": self.scene.add_gif,
            "SOUND": self.scene.add_sound,
            "VIDEO": self.scene.add_video,
            "WEB": self.scene.add_web
        }
        for scene_dict in scene.values():
            scene_widget_type = scene_dict.get("type")
            function = scene_add_function.get(scene_widget_type)
            function(setting_dict=scene_dict)
        monitors = QGuiApplication.screens()
        if self.show_all_screen is False and len(monitors) <= 1:
            graphic_view = ExtendGraphicView(self.scene.graphic_scene)
            self.scene.view_list.append(graphic_view)
            graphic_view.showMaximized()
        elif self.show_all_screen is False and len(monitors) >= 2:
            input_dialog, combobox = monitor_choose_dialog(self, monitors)
            result = input_dialog.exec_()
            if result == QDialog.DialogCode.Accepted:
                select_monitor_index = int(combobox.currentText())
                if len(monitors) > select_monitor_index:
                    monitor = monitors[select_monitor_index]
                    graphic_view = ExtendGraphicView(self.scene.graphic_scene)
                    graphic_view.setScreen(monitor)
                    graphic_view.move(monitor.availableGeometry().topLeft())
                    self.scene.view_list.append(graphic_view)
                    graphic_view.showMaximized()
        else:
            for monitor in monitors:
                graphic_view = ExtendGraphicView(self.scene.graphic_scene)
                graphic_view.setScreen(monitor)
                graphic_view.move(monitor.availableGeometry().topLeft())
                self.scene.view_list.append(graphic_view)
                graphic_view.showMaximized()

    def update_scene_json(self):
        choose_scene_json(self)
        self.renew_json_plain_text()

    def renew_json_plain_text(self):
        self.json_plaintext.setPlainText(json.dumps(scene_json, indent=4))
