from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTabWidget, QLabel, QPushButton

from frontengine.ui.page.layout_kit import SettingPage

from frontengine.show.scene.scene import SceneManager
from frontengine.ui.page.scene_setting.scene_manager import SceneManagerUI
from frontengine.ui.page.scene_setting.scene_page.registry import SCENE_PAGE_REGISTRY
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.ui.page.scene_setting.scene_visual_editor import SceneVisualEditor
from frontengine.utils.multi_language.retranslate import retranslator, tr
from frontengine.ui.page.scene_setting.scene_actions import SceneActions


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
        self.actions = SceneActions(self)
        self.templates_dialog = None
        self.output_dialog = None
        output_button = tr(QPushButton(), 'scene_camera_output')
        output_button.clicked.connect(self.open_output)
        self.add_body_widget(output_button)
        self.scene_manager_ui.templates_requested.connect(self.open_templates)
        self.action_status = QLabel()
        self.action_status.setWordWrap(True)
        self.add_body_widget(self.action_status)
        self.actions.status_changed.connect(self._action_status)
        self._action_status('')

    def _action_status(self, error: str) -> None:
        if error:
            self.action_status.setText(error)
        else:
            key = 'scene_action_loading' if self.actions.pending is not None else 'scene_action_ready'
            retranslator.set_text(self.action_status, key)

    def close_scene(self) -> None:
        front_engine_logger.info("[SceneSettingUI] close_scene")
        self.actions.stop_playback()

    def shutdown_scene(self) -> None:
        """Close playback and previews before releasing extracted scene resources."""
        if self.templates_dialog is not None:
            self.templates_dialog.close()
        if self.output_dialog is not None:
            self.output_dialog.close()
        self.actions.shutdown()

    def open_output(self) -> None:
        """Preview/send a snapshot of the editor independently of desktop playback."""
        from frontengine.ui.dialog.scene_output_dialog import SceneOutputDialog
        if self.output_dialog is None:
            self.output_dialog = SceneOutputDialog(self.visual_editor.document, self)
        self.output_dialog.show()
        self.output_dialog.raise_()
        self.output_dialog.activateWindow()

    def open_templates(self) -> None:
        """Reuse one local template library with layout preview and screen choice."""
        from frontengine.ui.dialog.scene_templates_dialog import SceneTemplatesDialog
        if self.templates_dialog is None:
            self.templates_dialog = SceneTemplatesDialog(self)
        self.templates_dialog.show()
        self.templates_dialog.raise_()
        self.templates_dialog.activateWindow()

    def closeEvent(self, event) -> None:
        self.shutdown_scene()
        super().closeEvent(event)
