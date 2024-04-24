from PySide6.QtWidgets import QWidget, QGridLayout

from frontengine.ui.page.scene_setting.scene_manager import SceneManagerUI
from frontengine.user_setting.scene_setting import scene_json


class WebSceneSettingUI(QWidget):

    def __init__(self, script_ui: SceneManagerUI):
        super().__init__()
        self.script_ui = script_ui
        self.grid_layout = QGridLayout()
        self.setLayout(self.grid_layout)

    def update_scene_json(self):
        scene_json.update(
            {
                "WEB": {

                }
            }
        )
        self.script_ui.update_scene_json()
