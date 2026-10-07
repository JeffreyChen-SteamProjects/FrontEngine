from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTabWidget

from frontengine.ui.page.layout_kit import SettingPage

from frontengine.show.scene.scene import SceneManager
from frontengine.ui.page.scene_setting.scene_manager import SceneManagerUI
from frontengine.ui.page.scene_setting.scene_page.registry import SCENE_PAGE_REGISTRY
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.ui.page.scene_setting.scene_visual_editor import SceneVisualEditor
from frontengine.utils.multi_language.retranslate import retranslator


class SceneSettingUI(SettingPage):
    def __init__(self):
        front_engine_logger.info("[SceneSettingUI] Init")
        super().__init__("tab_scene_text", "page_subtitle_scene",
                         "Scene", "Arrange several overlays together as one scene.")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # scene
        self.scene = SceneManager()

        # Tab
        self.tab_widget = QTabWidget(self)
        self.scene_manager_ui = SceneManagerUI(self.scene)
        self.visual_editor = SceneVisualEditor(self.scene_manager_ui)
        visual_index = self.tab_widget.addTab(self.visual_editor, "")
        retranslator.bind(self.tab_widget, "scene_visual_editor", "", "setTabText", visual_index)
        self.tab_widget.addTab(
            self.scene_manager_ui, language_wrapper.language_word_dict.get("scene_script")
        )

        for ui_class, label_key in SCENE_PAGE_REGISTRY:
            self.tab_widget.addTab(ui_class(self.scene_manager_ui), language_wrapper.language_word_dict.get(label_key))

        # 場景的子分頁留著：那是「這個場景裡有哪些東西」，和主導覽是不同層次的
        # 選擇，攤平反而看不出它們屬於同一個場景。
        # The scene keeps its own sub-tabs: they are what this scene contains,
        # a different kind of choice from the main navigation, and flattening
        # them would hide that they belong to one scene.
        self.add_body_widget(self.tab_widget, 1)

    def close_scene(self) -> None:
        front_engine_logger.info("[SceneSettingUI] close_scene")
        views = tuple(self.scene.view_list)
        self.scene.view_list.clear()
        for view in views:
            try:
                view.close()
                view.deleteLater()
            except RuntimeError:  # A manually closed view may already be deleted.
                continue
        # Stop render timers before deleting the proxies they read.
        self.scene.clear()
