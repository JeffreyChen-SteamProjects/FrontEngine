from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QTabWidget

from frontengine.show.scene.scene import SceneManager
from frontengine.ui.page.scene_setting.scene_manager import SceneManagerUI
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class SceneSettingUI(QWidget):

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.grid_layout = QGridLayout()
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        # scene
        self.scene = SceneManager()
        # Tab
        self.tab_widget = QTabWidget(self)
        self.tab_widget.addTab(
            SceneManagerUI(), language_wrapper.language_word_dict.get("scene_script")
        )
        # Add to layout
        self.grid_layout.addWidget(self.tab_widget, 0, 0, -1, -1)
        self.setLayout(self.grid_layout)

    def close_scene(self) -> None:
        self.scene.widget_list.clear()
        if self.scene.graphic_view.isEnabled() and self.scene.graphic_view.isVisible():
            self.scene.graphic_view.close()
