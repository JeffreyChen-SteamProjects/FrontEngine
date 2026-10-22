"""Settings remain usable when windows narrow or translated labels grow."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QCheckBox, QLabel, QLineEdit, QPushButton, QSlider

from frontengine.ui.page.layout_kit import SettingPage


def settle_layout():
    for _ in range(3):
        QApplication.processEvents()


def test_form_wraps_and_returns_to_columns_without_losing_values():
    page = SettingPage("tab_video_text")
    section = page.add_section("section_appearance")
    label, field = QLabel("Target monitor"), QLineEdit("Display 1")
    section.add_row(label, field)
    slider_label, slider, value = QLabel("Opacity"), QSlider(Qt.Orientation.Horizontal), QLabel("65")
    slider.setValue(65)
    section.add_slider_row(slider_label, slider, value)
    page.finish_body()
    page.set_footer(primary=QPushButton("Start"))
    try:
        page.resize(850, 500)
        page.show()
        settle_layout()
        assert field.geometry().left() > label.geometry().right()
        page.resize(430, 500)
        settle_layout()
        assert field.geometry().top() > label.geometry().bottom()
        slider_top = slider.mapTo(section, slider.rect().topLeft()).y()
        assert slider_top > slider_label.geometry().bottom()
        assert page._scroll.horizontalScrollBar().maximum() == 0
        viewport = page._scroll.viewport()
        for widget in (field, slider, value):
            assert viewport.rect().contains(widget.mapTo(viewport, widget.rect().bottomRight()))
        assert field.text() == "Display 1" and slider.value() == 65
        assert label.buddy() is field and slider_label.buddy() is slider
        page.resize(850, 500)
        settle_layout()
        assert field.geometry().left() > label.geometry().right()
    finally:
        page.close()


def test_wide_custom_content_can_be_reached_by_scrolling():
    page = SettingPage("tab_video_text")
    content = QLineEdit("Wide custom content")
    content.setMinimumWidth(800)
    page.add_body_widget(content)
    page.finish_body()
    button = QPushButton("Start")
    page.set_footer(primary=button)
    try:
        page.resize(430, 400)
        page.show()
        settle_layout()
        scrollbar = page._scroll.horizontalScrollBar()
        assert scrollbar.maximum() > 0 and scrollbar.isVisible()
        scrollbar.setValue(scrollbar.maximum())
        settle_layout()
        viewport = page._scroll.viewport()
        assert viewport.rect().contains(content.mapTo(viewport, content.rect().bottomRight()))
        assert button.isVisible() and page.rect().contains(button.mapTo(page, button.rect().bottomRight()))
    finally:
        page.close()


def test_inline_controls_wrap_and_hidden_controls_leave_no_gap():
    page = SettingPage("tab_video_text")
    section = page.add_section("section_where")
    controls = [QCheckBox(text) for text in (
        "All monitors", "Behind windows", "Fullscreen")]
    for control in controls:
        control.setFixedWidth(180)
    section.add_inline(*controls)
    page.finish_body()
    try:
        page.resize(850, 500)
        page.show()
        settle_layout()
        assert len({widget.y() for widget in controls}) == 1
        page.resize(360, 500)
        settle_layout()
        assert controls[1].y() > controls[0].y()
        assert page._scroll.horizontalScrollBar().maximum() == 0
        controls[0].hide()
        settle_layout()
        assert controls[1].y() == 0
        page.resize(850, 500)
        settle_layout()
        assert controls[1].y() == controls[2].y()
    finally:
        page.close()
