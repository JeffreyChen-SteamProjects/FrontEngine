"""The tools page says what each tool does, and the full-screen tools say what to do and how to leave."""
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLabel

from frontengine.show.capture.region_capture import RegionCaptureWidget
from frontengine.show.measure.measure_widget import MODE_ANGLE, MODE_COLOR, MODE_RULER, MODES, MeasureWidget
from frontengine.show.overlay_hint import draw_hint
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import retranslator
from frontengine.utils.screen_text.screen_text_service import ACTION_ASK, ACTION_EXTRACT, ACTION_TRANSLATE


@pytest.fixture
def page(make_main_window):
    return make_main_window().tools_setting_ui


def test_every_tool_section_opens_with_what_it_is_for(page):
    from frontengine.ui.page.layout_kit import Section
    sections = page.findChildren(Section)
    assert len(sections) == 7
    for section in sections:
        assert section.findChildren(QLabel, "sectionNote"), section.title_label.text()


def test_the_explanation_follows_the_choice_and_the_language(page):
    words = language_wrapper.language_word_dict
    for mode in MODES:
        page.measure_mode_combobox.setCurrentIndex(page.measure_mode_combobox.findData(mode))
        assert page.measure_help.text() == words[f"tools_measure_help_{mode}"]
        assert page.color_format_combobox.isHidden() == (mode != MODE_COLOR)
    page.record_format.setCurrentIndex(page.record_format.findData("avi"))
    assert page.record_format_help.text() == words["tools_record_help_avi"]
    previous = language_wrapper.language
    try:
        language_wrapper.reset_language("Traditional_Chinese")
        retranslator.apply()
        assert page.measure_help.text() == language_wrapper.language_word_dict[f"tools_measure_help_{MODES[-1]}"]
    finally:
        language_wrapper.reset_language(previous)
        retranslator.apply()


def test_the_language_and_the_question_are_separate_and_hidden_when_not_needed(page):
    combo, box = page.screen_text_combobox, page.screen_text_input
    words = language_wrapper.language_word_dict
    assert combo.currentData() == ACTION_EXTRACT and box.isHidden()
    combo.setCurrentIndex(combo.findData(ACTION_TRANSLATE))
    language = box.text()
    assert language and not box.isHidden()
    assert page.screen_text_input_label.text() == words["tools_screen_text_language"]
    combo.setCurrentIndex(combo.findData(ACTION_ASK))
    assert box.text() == ""                          # the language is not a question
    assert page.screen_text_input_label.text() == words["tools_screen_text_question"]
    box.setText("What is this?")
    combo.setCurrentIndex(combo.findData(ACTION_TRANSLATE))
    assert box.text() == language
    combo.setCurrentIndex(combo.findData(ACTION_ASK))
    assert box.text() == "What is this?"


@pytest.mark.parametrize("mode", [MODE_COLOR, MODE_RULER, MODE_ANGLE])
def test_the_measuring_layer_catches_clicks_and_says_what_to_do(mode):
    """Fully transparent pixels hand the click to the program underneath: nothing was ever measured."""
    widget = MeasureWidget(mode)
    widget.resize(700, 300)
    image = widget._raster_content()
    assert 0 < image.pixelColor(690, 290).alpha() < 8
    assert any(image.pixelColor(350, y).alpha() > 200 for y in range(30, 110))     # the instruction banner
    widget.set_ui_variable(0.2)                      # a lowered opacity must not round the catch alpha to 0
    assert widget._raster_content().pixelColor(690, 290).alpha() > 0
    widget.close()


def test_escape_leaves_the_measuring_layer(page):
    page.start_measure()
    widget = page.measure_widget_list[0]
    QTest.keyClick(widget, Qt.Key.Key_Escape)
    assert page.measure_widget_list == []


def test_the_ruler_counts_real_screen_pixels(monkeypatch):
    widget = MeasureWidget(MODE_RULER)
    monkeypatch.setattr(widget, "devicePixelRatioF", lambda: 1.5, raising=False)
    widget.add_point(QPoint(0, 0))
    assert widget.add_point(QPoint(100, 40)).startswith("150 x 60 px")
    widget.close()


def test_escape_cancels_a_region_selection_without_capturing():
    captured = []
    widget = RegionCaptureWidget(on_captured=lambda *args: captured.append(args), prompt_key="region_prompt_record")
    widget.resize(700, 300)
    widget.show()
    image = widget._raster_content()
    assert any(image.pixelColor(350, y).alpha() > 200 for y in range(30, 110))
    widget.begin(QPoint(10, 10))
    widget.extend(QPoint(600, 250))
    assert widget._raster_content().pixelColor(350, 60).alpha() == 0     # gone once the drag starts
    QTest.keyClick(widget, Qt.Key.Key_Escape)
    assert not widget.isVisible() and captured == []


def test_each_region_tool_names_its_own_task(page):
    prompts = []
    for start in (page.start_capture, page.start_recording, page.start_screen_text, page.start_live_ocr,
                  page.start_virtual_camera):
        picker = start()
        prompts.append(picker.prompt_key)
        picker.close()
    assert len(set(prompts)) == 5
    for key in prompts:
        assert key in language_wrapper.language_word_dict


def test_a_hint_wider_than_the_screen_wraps_inside_it():
    image = QImage(320, 240, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    draw_hint(painter, image.rect(), "Click the first arm, the corner, the second arm, then press Esc to finish")
    painter.end()
    assert all(image.pixelColor(x, y).alpha() == 0 for x in (0, 319) for y in range(0, 240, 10))
