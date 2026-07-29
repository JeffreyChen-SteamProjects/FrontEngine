import json

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget, QGridLayout, QPlainTextEdit, QPushButton, QCheckBox, QDialog, QMessageBox

from frontengine.show.scene.extend_graphic_view import ExtendGraphicView
from frontengine.ui.page.utils import create_monitor_selection_dialog
from frontengine.user_setting.scene_setting import choose_scene_json, write_scene_file, scene_json
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.retranslate import tr


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
        self.read_scene_json_button = tr(QPushButton(), "scene_input")
        self.read_scene_json_button.clicked.connect(self.update_scene_json)

        self.write_scene_json_button = tr(QPushButton(), "scene_output")
        self.write_scene_json_button.clicked.connect(lambda: write_scene_file(self))

        # Json plaintext
        self.json_plaintext = QPlainTextEdit()
        self.json_plaintext.setReadOnly(True)
        self.json_plaintext.appendPlainText("{}")

        # Start button
        self.start_button = tr(QPushButton(), "scene_start")
        self.start_button.clicked.connect(self.start_scene)

        # Show on all screen
        self.show_on_all_screen_checkbox = tr(QCheckBox(), "Show on all screen")
        self.show_on_all_screen_checkbox.clicked.connect(self.set_show_all_screen)

        # Clear json button
        self.clear_json_button = tr(QPushButton(), "scene_script_clear")
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
        """
        清空腳本。也要清掉 scene_json 本身：只清編輯框的話，下一次從分頁加入
        項目時 _append_scene 會寫進還留著舊資料的那個 dict，畫面上「清掉的」
        東西又全部長回來。
        Clear the script. scene_json itself has to go too: with only the text box
        emptied, the next item added from a tab writes into a dict that still
        holds the old entries, and everything the user just cleared reappears.
        """
        front_engine_logger.info("[SceneManagerUI] clear_json")
        scene_json.clear()
        self.json_plaintext.clear()

    def start_scene(self):
        front_engine_logger.info("[SceneManagerUI] start_scene")
        scene = self._parse_scene_json()
        if scene is None:
            return
        # 先決定要開在哪台螢幕，再建立元件。反過來的話，使用者在螢幕選擇對話框
        # 按取消就會留下一整組看不見卻在播放的元件，下次開始場景還會看到雙份。
        # Settle on the target screen before building anything. The other way
        # round, cancelling the monitor dialog leaves a full set of invisible but
        # playing widgets behind, and the next start shows everything twice.
        monitors = self._choose_monitors(QGuiApplication.screens())
        if monitors is None:
            return
        self._add_scene_widgets(scene)
        for monitor in monitors:
            self._open_view(monitor)

    def _parse_scene_json(self):
        """讀出編輯框裡的場景 JSON；格式錯誤就告訴使用者並回傳 None。"""
        text = self.json_plaintext.toPlainText().strip()
        if not text:
            # 空白的腳本就是「沒有東西要開」，不是語法錯誤
            # An empty script means "nothing to open", not a syntax error.
            return {}
        try:
            scene = json.loads(text)
        except json.JSONDecodeError as error:
            QMessageBox.critical(self, "JSON Error", f"Invalid JSON: {error}")
            return None
        if not isinstance(scene, dict):
            QMessageBox.critical(
                self, "JSON Error",
                f"A scene must be an object of entries, not {type(scene).__name__}")
            return None
        return scene

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
            if not isinstance(scene_dict, dict):
                QMessageBox.warning(
                    self, "Invalid Scene Entry",
                    f"A scene entry must be an object, not {type(scene_dict).__name__}")
                continue
            scene_widget_type = scene_dict.get("type")
            function = scene_add_function.get(scene_widget_type)
            if function is None:
                QMessageBox.warning(
                    self, "Unknown Type", f"Unsupported scene type: {scene_widget_type}")
                continue
            try:
                function(setting_dict=scene_dict)
            except ValueError as error:
                # 手寫的場景檔漏欄位是常態，指出哪一項壞掉就好，不要整個中斷
                # A hand-written scene file missing a field is routine: name the
                # broken entry and carry on rather than aborting the whole run.
                QMessageBox.warning(self, "Invalid Scene Entry", str(error))

    def _choose_monitors(self, monitors: list):
        """
        決定場景要開在哪些螢幕上：勾了「所有螢幕」就全部；只有一台就直接開；
        多台時先問使用者。使用者取消（或選了不存在的編號）回傳 None，代表
        「這次不要開」——和「開在主螢幕」的空清單不一樣。
        Which monitors the scene opens on: all of them when "all screens" is
        ticked, the only one when there is only one, otherwise whichever the user
        picks. None means the user backed out, which is different from the
        single-element list that means the primary screen.
        """
        if self.show_all_screen:
            return list(monitors)
        if len(monitors) <= 1:
            return [None]
        input_dialog, combobox = create_monitor_selection_dialog(self, monitors)
        if input_dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        index = int(combobox.currentText())
        if index >= len(monitors):
            return None
        return [monitors[index]]

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
        try:
            choose_scene_json(self)
        except OSError as error:
            # 選到壞掉或讀不到的場景檔。不接住的話畫面完全沒反應，
            # 使用者只會覺得那個按鈕壞了。
            # A scene file that is corrupt or unreadable. Uncaught, nothing at all
            # happens on screen and the button just looks broken.
            QMessageBox.critical(self, "Scene Error", f"Cannot read that scene file: {error}")
            return
        self.renew_json_plain_text()

    def renew_json_plain_text(self):
        front_engine_logger.info("[SceneManagerUI] renew_json_plain_text")
        self.json_plaintext.setPlainText(json.dumps(scene_json, indent=4))