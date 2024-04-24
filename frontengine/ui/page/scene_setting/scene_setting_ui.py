from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QTabWidget

from frontengine.ui.page.scene_setting.scene_page.scene_manager import SceneManagerUI
from frontengine.utils.multi_language.language_wrapper import language_wrapper


class SceneSettingUI(QWidget):

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.grid_layout = QGridLayout()
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        # Tab
        self.tab_widget = QTabWidget(self)
        self.tab_widget.addTab(
            SceneManagerUI(), language_wrapper.language_word_dict.get("scene_script")
        )
        # Add to layout
        self.grid_layout.addWidget(self.tab_widget, 0, 0, -1, -1)
        self.setLayout(self.grid_layout)
