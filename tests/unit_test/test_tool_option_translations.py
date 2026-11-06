"""Translated option labels follow language changes without changing settings."""
import pytest

from frontengine.ui.menu.language_menu import LANGUAGES
from frontengine.utils.multi_language.retranslate import translate


@pytest.mark.parametrize('page_name, attribute, keys', [
    ('control_center_ui', 'quality_combobox',
     ('control_center_quality_high', 'control_center_quality_balanced', 'control_center_quality_saver')),
    ('tools_setting_ui', 'measure_mode_combobox',
     ('tools_measure_color', 'tools_measure_ruler', 'tools_measure_angle')),
    ('tools_setting_ui', 'screen_text_combobox',
     ('tools_screen_text_extract', 'tools_screen_text_translate', 'tools_screen_text_ask')),
    ('tools_setting_ui', 'camera_shape_combobox',
     ('tools_camera_circle', 'tools_camera_rounded', 'tools_camera_rectangle')),
    ('widgets_setting_ui', 'spectrum_style_combobox',
     ('widgets_spectrum_bars', 'widgets_spectrum_ring')),
])
def test_tool_option_labels_follow_language_without_changing_selection(
        make_main_window, page_name, attribute, keys):
    window = make_main_window()
    combo = getattr(getattr(window, page_name), attribute)
    combo.setCurrentIndex(combo.count() - 1)
    selected = combo.currentData()
    values = [combo.itemData(i) for i in range(combo.count())]
    changes = []
    combo.currentIndexChanged.connect(changes.append)
    try:
        for index in [*range(len(LANGUAGES)), 0]:
            window.language_menu.actions()[index].trigger()
            assert [combo.itemText(i) for i in range(combo.count())] == [translate(key) for key in keys]
            assert combo.currentData() == selected
            assert [combo.itemData(i) for i in range(combo.count())] == values
            assert not changes
    finally:
        window.language_menu.actions()[0].trigger()


@pytest.mark.parametrize('attribute, keys', [
    ('tool', ('scene3d_move', 'scene3d_rotate', 'scene3d_scale')),
    ('axis', ('scene3d_free', 'scene3d_x', 'scene3d_y', 'scene3d_z')),
    ('space', ('scene3d_world', 'scene3d_screen')),
    ('projection', ('scene3d_perspective', 'scene3d_orthographic')),
    ('light_type', ('scene3d_directional', 'scene3d_point')),
])
def test_scene_option_labels_follow_language_without_editing_document(
        make_main_window, attribute, keys):
    window = make_main_window()
    editor = window.scene_setting_ui.visual_editor
    combo = getattr(editor.editor3d, attribute)
    fallbacks = [combo.itemText(i) for i in range(combo.count())]
    combo.setCurrentIndex(combo.count() - 1)
    selected = combo.currentData()
    values = [combo.itemData(i) for i in range(combo.count())]
    scene = editor.document.scene.copy().envelope()
    undo_index = editor.document.undo.index()
    changes = []
    combo.currentIndexChanged.connect(changes.append)
    try:
        for index in [*range(len(LANGUAGES)), 0]:
            window.language_menu.actions()[index].trigger()
            assert [combo.itemText(i) for i in range(combo.count())] == [
                translate(key, fallback) for key, fallback in zip(keys, fallbacks)]
            assert combo.currentData() == selected
            assert [combo.itemData(i) for i in range(combo.count())] == values
            assert editor.document.scene.envelope() == scene
            assert editor.document.undo.index() == undo_index
            assert not changes
    finally:
        window.language_menu.actions()[0].trigger()


@pytest.mark.parametrize('selected_tab', range(9))
def test_scene_tab_labels_follow_language_without_replacing_pages(make_main_window, selected_tab):
    from frontengine.ui.page.scene_setting.scene_page.registry import SCENE_PAGE_REGISTRY

    window = make_main_window()
    page = window.scene_setting_ui
    tabs = page.tab_widget
    keys = ['scene_visual_editor', 'scene_script', *[key for _, key in SCENE_PAGE_REGISTRY]]
    assert tabs.count() == len(keys)
    page.visual_editor.document.add({'type': 'TEXT', 'text': 'Keep this scene'}, 'Add text')
    tabs.setCurrentIndex(selected_tab)
    widgets = [tabs.widget(i) for i in range(tabs.count())]
    scene = page.visual_editor.document.scene.copy().envelope()
    script = page.scene_manager_ui.json_plaintext.toPlainText()
    undo_index = page.visual_editor.document.undo.index()
    changes = []
    tabs.currentChanged.connect(changes.append)
    try:
        for index in [*range(len(LANGUAGES)), 0]:
            window.language_menu.actions()[index].trigger()
            assert [tabs.tabText(i) for i in range(tabs.count())] == [translate(key) for key in keys]
            assert tabs.currentIndex() == selected_tab
            assert [tabs.widget(i) for i in range(tabs.count())] == widgets
            assert page.visual_editor.document.scene.envelope() == scene
            assert page.scene_manager_ui.json_plaintext.toPlainText() == script
            assert page.visual_editor.document.undo.index() == undo_index
            assert not changes
    finally:
        window.language_menu.actions()[0].trigger()
