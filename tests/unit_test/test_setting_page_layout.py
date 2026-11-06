"""Settings remain usable when windows narrow or translated labels grow."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QCheckBox, QLabel, QLineEdit, QPushButton, QSlider

from frontengine.ui.page.layout_kit import SettingPage


def settle_layout():
    for _ in range(3):
        QApplication.processEvents()


def test_form_wraps_and_returns_to_columns_without_losing_values(*, lifetime_factory):
    lifetime_factory()
    page = SettingPage("tab_video_text", lifetime=lifetime_factory())
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


def test_wide_custom_content_can_be_reached_by_scrolling(*, lifetime_factory):
    lifetime_factory()
    page = SettingPage("tab_video_text", lifetime=lifetime_factory())
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


def test_inline_controls_wrap_and_hidden_controls_leave_no_gap(*, lifetime_factory):
    lifetime_factory()
    page = SettingPage("tab_video_text", lifetime=lifetime_factory())
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


def test_content_section_reflows_and_settles_after_height_changes():
    from PySide6.QtCore import QEvent, QObject
    from PySide6.QtWidgets import QVBoxLayout, QWidget
    from frontengine.ui.page.flow_layout import FlowLayout
    from frontengine.ui.page.layout_kit import ContentSection

    class LayoutRequests(QObject):
        count = 0

        def eventFilter(self, watched, event):
            if event.type() == QEvent.Type.LayoutRequest:
                self.count += 1
            return False

    host = QWidget()
    column = QVBoxLayout(host)
    section = ContentSection("Home")
    column.addWidget(section)
    view, toolbar, pending = QWidget(), QWidget(), QLabel("Waiting")
    view.setFixedHeight(234)
    flow = FlowLayout(toolbar, spacing=10)
    for caption in ("Back to the desktop", "Backpack", "Goals", "-", "+"):
        flow.addWidget(QPushButton(caption))
    for widget in (view, toolbar, pending):
        section.add_widget(widget)
    observer = LayoutRequests(host)
    for widget in (host, section, section.content):
        widget.installEventFilter(observer)
    try:
        host.show()
        for width in (400, 980, 400):
            for height in (120, 60, 30, 120):
                pending.setFixedHeight(height)
                settle_layout()
                host.resize(width, host.heightForWidth(width))
                settle_layout()
                assert toolbar.y() > view.geometry().bottom()
                assert pending.y() > toolbar.geometry().bottom()
        settle_layout()
        before = observer.count
        for _ in range(100):
            QApplication.processEvents()
        assert observer.count == before
    finally:
        host.close()
        host.deleteLater()


def test_section_heading_wraps_without_losing_toggle_or_field_value(*, lifetime_factory):
    from PySide6.QtTest import QTest
    page = SettingPage('tab_pet_text', lifetime=lifetime_factory())
    section = page.add_section(QLabel('More ways to add a pet'), collapsed=True)
    field = QLineEdit('Keep this value')
    section.add_row('Name', field)
    page.finish_body()
    try:
        page.resize(850, 600)
        page.show()
        settle_layout()
        assert section.toggle_button.y() == section.title_label.y()
        page.resize(350, 600)
        settle_layout()
        assert section.toggle_button.y() > section.title_label.geometry().bottom()
        viewport = page._scroll.viewport()
        assert viewport.rect().contains(section.toggle_button.mapTo(viewport, section.toggle_button.rect().bottomRight()))
        assert page._scroll.horizontalScrollBar().maximum() == 0
        section.toggle_button.setFocus()
        QTest.keyClick(section.toggle_button, Qt.Key.Key_Space)
        settle_layout()
        assert section.content.isVisible() and field.text() == 'Keep this value'
        page.resize(850, 600)
        settle_layout()
        assert section.toggle_button.y() == section.title_label.y()
        assert field.text() == 'Keep this value'
    finally:
        page.close()
