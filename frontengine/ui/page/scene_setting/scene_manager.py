import json

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget, QGridLayout, QPlainTextEdit, QPushButton, QCheckBox, QDialog, QMessageBox

from frontengine.show.scene.extend_graphic_view import ExtendGraphicView
from frontengine.ui.page.utils import create_monitor_selection_dialog
from frontengine.user_setting.scene_setting import choose_scene_json, write_scene_file, scene_json
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import retranslator


class SceneManagerUI(QWidget):
    def __init__(self, scene_manager):
        front_engine_logger.info("[SceneManagerUI] Init")
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.scene = scene_manager
        self.show_all_screen = False

        # Read and write scene json button
        self.read_scene_json_button = QPushButton(language_wrapper.language_word_dict.get("scene_input"))
        retranslator.bind(self.read_scene_json_button, "scene_input", "")
        self.read_scene_json_button.clicked.connect(self.update_scene_json)

        self.write_scene_json_button = QPushButton(language_wrapper.language_word_dict.get("scene_output"))
        retranslator.bind(self.write_scene_json_button, "scene_output", "")
        self.write_scene_json_button.clicked.connect(lambda: write_scene_file(self))

        # Json plaintext
        self.json_plaintext = QPlainTextEdit()
        self.json_plaintext.setReadOnly(True)
        self.json_plaintext.appendPlainText("{}")

        # Start button
        self.start_button = QPushButton(language_wrapper.language_word_dict.get("scene_start"))
        retranslator.bind(self.start_button, "scene_start", "")
        self.start_button.clicked.connect(self.start_scene)

        # Show on all screen
        self.show_on_all_screen_checkbox = QCheckBox(language_wrapper.language_word_dict.get("Show on all screen"))
        retranslator.bind(self.show_on_all_screen_checkbox, "Show on all screen", "")
        self.show_on_all_screen_checkbox.clicked.connect(self.set_show_all_screen)

        # Clear json button
        self.clear_json_button = QPushButton(language_wrapper.language_word_dict.get("scene_script_clear"))
        retranslator.bind(self.clear_json_button, "scene_script_clear", "")
        self.clear_json_button.clicked.connect(self.clear_json)

        # Layout
        self.grid_layout.addWidget(self.json_plaintext, 0, 0, 4, 2)
        self.grid_layout.addWidget(self.read_scene_json_button, 4, 0)
        self.grid_layout.addWidget(self.write_scene_json_button, 4, 1)
        self.grid_layout.addWidget(self.show_on_all_screen_checkbox, 5, 0)
        self.grid_layout.addWidget(self.clear_json_button, 5, 1)
        self.grid_layout.addWidget(self.start_button, 6, 0)

    def set_show_all_screen(self) -> None:
        front_engine_logger.info("[SceneManagerUI] set_show_all_screen")
        self.show_all_screen = self.show_on_all_screen_checkbox.isChecked()

    def clear_json(self) -> None:
        front_engine_logger.info("[SceneManagerUI] clear_json")
        self.json_plaintext.clear()

    def start_scene(self):
        front_engine_logger.info("[SceneManagerUI] start_scene")
        scene = self._parse_scene_json()
        if scene is None:
            return
        self._add_scene_widgets(scene)
        self._present_scene(QGuiApplication.screens())

    def _parse_scene_json(self):
        """讀出編輯框裡的場景 JSON；格式錯誤就告訴使用者並回傳 None。"""
        try:
            return json.loads(self.json_plaintext.toPlainText())
        except json.JSONDecodeError as error:
            QMessageBox.critical(self, "JSON Error", f"Invalid JSON: {error}")
            return None

    def _add_scene_widgets(self, scene: dict) -> None:
        """把場景描述裡的每個項目加進場景；不認得的型別會提醒使用者。"""
        scene_add_function = {
            "TEXT": self.scene.add_text,
            "IMAGE": self.scene.add_image,
            "GIF": self.scene.add_gif,
            "SOUND": self.scene.add_sound,
            "VIDEO": self.scene.add_video,
            "WEB": self.scene.add_web,
        }
        for scene_dict in scene.values():
            scene_widget_type = scene_dict.get("type")
            function = scene_add_function.get(scene_widget_type)
            if function is None:
                QMessageBox.warning(
                    self, "Unknown Type", f"Unsupported scene type: {scene_widget_type}")
                continue
            function(setting_dict=scene_dict)

    def _present_scene(self, monitors: list) -> None:
        """
        決定場景要開在哪裡：勾了「所有螢幕」就每台都開；否則只有一台螢幕時
        直接開，多台時先問使用者要哪一台。
        Where the scene opens: every monitor when "all screens" is ticked,
        straight up with only one monitor, and otherwise after asking which.
        """
        if self.show_all_screen:
            for monitor in monitors:
                self._open_view(monitor)
            return
        if len(monitors) <= 1:
            self._open_view(None)
            return
        input_dialog, combobox = create_monitor_selection_dialog(self, monitors)
        if input_dialog.exec() != QDialog.DialogCode.Accepted:
            return
        index = int(combobox.currentText())
        if index < len(monitors):
            self._open_view(monitors[index])

    def _open_view(self, monitor) -> None:
        """開一個場景視窗；給了螢幕就擺到那台上面。"""
        graphic_view = ExtendGraphicView(self.scene.graphic_scene)
        if monitor is not None:
            graphic_view.setScreen(monitor)
            graphic_view.move(monitor.availableGeometry().topLeft())
        self.scene.view_list.append(graphic_view)
        graphic_view.showMaximized()

    def update_scene_json(self):
        front_engine_logger.info("[SceneManagerUI] update_scene_json")
        choose_scene_json(self)
        self.renew_json_plain_text()

    def renew_json_plain_text(self):
        front_engine_logger.info("[SceneManagerUI] renew_json_plain_text")
        self.json_plaintext.setPlainText(json.dumps(scene_json, indent=4))