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


@pytest.mark.parametrize('page_key, attribute, key', [
    ('tab_focus_text', 'target_monitor_combobox', 'target_monitor_here'),
    ('tab_gif_text', 'recent_files_combobox', 'recent_files_label'),
    ('tab_gif_text', 'target_monitor_combobox', 'target_monitor_here'),
    ('tab_image_text', 'recent_files_combobox', 'recent_files_label'),
    ('tab_image_text', 'target_monitor_combobox', 'target_monitor_here'),
    ('tab_particle_text', 'recent_files_combobox', 'recent_files_label'),
    ('tab_particle_text', 'target_monitor_combobox', 'target_monitor_here'),
    ('tab_pet_text', 'recent_files_combobox', 'recent_files_label'),
    ('tab_pet_text', 'target_monitor_combobox', 'target_monitor_here'),
    ('tab_presentation_text', 'target_monitor_combobox', 'target_monitor_here'),
    ('tab_screen_care_text', 'target_monitor_combobox', 'target_monitor_here'),
    ('tab_text_text', 'target_monitor_combobox', 'target_monitor_here'),
    ('tab_video_text', 'recent_files_combobox', 'recent_files_label'),
    ('tab_video_text', 'target_monitor_combobox', 'target_monitor_here'),
    ('tab_web_text', 'target_monitor_combobox', 'target_monitor_here'),
])
def test_shared_option_labels_follow_language_without_selection_changes(
        make_main_window, page_key, attribute, key):
    window = make_main_window()
    page = next(widget for widget, name, _ in window.command_pages if name == page_key)
    combo = getattr(page, attribute)
    combo.setCurrentIndex(combo.count() - 1)
    selected = combo.currentData()
    values = [combo.itemData(i) for i in range(combo.count())]
    changes = []
    combo.currentIndexChanged.connect(changes.append)
    try:
        for index in [*range(len(LANGUAGES)), 0]:
            window.language_menu.actions()[index].trigger()
            assert combo.itemText(0) == translate(key)
            assert combo.currentData() == selected
            assert [combo.itemData(i) for i in range(combo.count())] == values
            assert not changes
    finally:
        window.language_menu.actions()[0].trigger()


def test_shared_monitor_span_label_keeps_target_on_language_change(make_main_window):
    from frontengine.ui.page.utils import build_target_monitor_combobox, SPAN_ALL_DATA

    window = make_main_window()
    combo = build_target_monitor_combobox(screens=[object(), object()])
    combo.setParent(window)
    combo.setCurrentIndex(combo.findData(SPAN_ALL_DATA))
    changes = []
    combo.currentIndexChanged.connect(changes.append)
    try:
        for index in [*range(len(LANGUAGES)), 0]:
            window.language_menu.actions()[index].trigger()
            assert combo.itemText(0) == translate('target_monitor_here')
            assert combo.itemText(3) == translate('target_monitor_span')
            assert [combo.itemData(i) for i in range(combo.count())] == [None, 0, 1, SPAN_ALL_DATA]
            assert combo.currentData() == SPAN_ALL_DATA
            assert not changes
    finally:
        window.language_menu.actions()[0].trigger()


def test_shared_recent_placeholder_follows_language_after_reload(make_main_window, monkeypatch):
    from frontengine.ui.page import utils

    window = make_main_window()
    paths = ['C:/media/first.png', 'C:/media/second.png']
    monkeypatch.setattr(utils, 'get_recent_files', lambda category: list(paths))
    combo = utils.build_recent_combobox('image')
    combo.setParent(window)
    changes = []
    combo.currentIndexChanged.connect(changes.append)
    try:
        for index in [*range(len(LANGUAGES)), 0]:
            paths.reverse()
            utils.reload_recent_combobox(combo, 'image')
            combo.setCurrentIndex(2)
            selected = combo.currentData()
            changes.clear()
            window.language_menu.actions()[index].trigger()
            assert combo.itemText(0) == translate('recent_files_label')
            assert [combo.itemData(i) for i in range(combo.count())] == [None, *paths]
            assert [combo.itemText(i) for i in (1, 2)] == [path.rsplit('/', 1)[1] for path in paths]
            assert combo.currentData() == selected
            assert not changes
    finally:
        window.language_menu.actions()[0].trigger()


@pytest.mark.parametrize('duration', [0, 12.5])
def test_scene_duration_label_follows_language_without_changing_value(make_main_window, duration):
    window = make_main_window()
    editor = window.scene_setting_ui.visual_editor
    spin = editor.editor3d.duration
    spin.setValue(duration)
    scene = editor.document.scene.copy().envelope()
    undo_index = editor.document.undo.index()
    changes = []
    spin.valueChanged.connect(changes.append)
    try:
        for index in [*range(len(LANGUAGES)), 0]:
            window.language_menu.actions()[index].trigger()
            assert spin.specialValueText() == translate('scene3d_auto', 'Automatic')
            assert spin.value() == duration
            assert editor.document.scene.envelope() == scene
            assert editor.document.undo.index() == undo_index
            assert not changes
    finally:
        window.language_menu.actions()[0].trigger()


@pytest.mark.parametrize('with_parent', [False, True])
def test_scene_parent_placeholder_follows_language_after_selection_rebuild(make_main_window, with_parent):
    window = make_main_window()
    editor = window.scene_setting_ui.visual_editor
    previous_scene = editor.document.scene.copy()
    editor.scene_mode.setCurrentIndex(1)
    group = editor.document.add({'type': 'GROUP'}, 'Add group')
    child = editor.document.add({'type': 'CUBE', 'parent': group if with_parent else None}, 'Add cube')
    editor._select_layer(child)
    combo = editor.editor3d.parent_box
    scene = editor.document.scene.copy().envelope()
    undo_index = editor.document.undo.index()
    changes = []
    combo.currentIndexChanged.connect(changes.append)
    try:
        for index in [*range(len(LANGUAGES)), 0]:
            editor._select_layer(group)
            editor._select_layer(child)
            values = [combo.itemData(i) for i in range(combo.count())]
            assert values == [None, group]
            changes.clear()
            window.language_menu.actions()[index].trigger()
            assert combo.itemText(0) == translate('scene3d_no_parent', 'No parent')
            assert combo.itemText(1) == group
            assert combo.currentData() == (group if with_parent else None)
            assert [combo.itemData(i) for i in range(combo.count())] == values
            assert editor.document.scene.envelope() == scene
            assert editor.document.undo.index() == undo_index
            assert not changes
    finally:
        window.language_menu.actions()[0].trigger()
        editor.document.reset(previous_scene)
