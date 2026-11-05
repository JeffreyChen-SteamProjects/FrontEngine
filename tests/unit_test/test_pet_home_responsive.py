"""A narrow home page keeps its welcome text and creation controls readable."""
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel

from frontengine.ui.menu.language_menu import LANGUAGES, set_language
from frontengine.ui.page.wrapping_buttons import WrappingCheckBox


def test_created_home_fits_actual_narrow_window_with_arial(make_main_window, request):
    import os
    from pathlib import Path
    import pytest
    from PySide6.QtGui import QFontDatabase, QFontInfo

    font_file = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts/arial.ttf'
    if not font_file.is_file():
        pytest.skip('Windows Arial regression fixture is unavailable')
    identifier = QFontDatabase.addApplicationFont(str(font_file))
    assert identifier >= 0
    request.addfinalizer(lambda: QFontDatabase.removeApplicationFont(identifier))
    window = make_main_window()
    font = window.font()
    font.setFamily('Arial')
    window.setFont(font)
    assert QFontInfo(window.font()).family() == 'Arial'
    window.resize(536, 500)
    window.show()
    page = window.pet_home_ui
    page.create_home()
    try:
        for _label, language in LANGUAGES:
            assert set_language(language, window)
            window.resize(536, 500)
            for key in page.tabs.keys():
                assert page.tabs.select(key)
                for _ in range(3):
                    QApplication.processEvents()
                assert window.width() == 536, (language, key, window.width())
                assert page._scroll.horizontalScrollBar().maximum() == 0, (language, key)
    finally:
        set_language('English', window)


def test_empty_home_fits_narrow_window_in_every_language(make_main_window):
    window = make_main_window()
    window.resize(536, 500)
    window.show()
    page = window.pet_home_ui
    intro = next(label for label in page.intro_section.findChildren(QLabel)
                 if label.wordWrap() and label is not page.intro_section.title_label)
    try:
        for _label, language in LANGUAGES:
            assert set_language(language, window)
            for _ in range(3):
                QApplication.processEvents()
            viewport = page._scroll.viewport()
            assert page._scroll.horizontalScrollBar().maximum() == 0, language
            for control in (page.intro_section.title_label, intro, page.status,
                            page.create_button, page.sandbox_button):
                left = control.mapTo(viewport, QPoint(0, 0)).x()
                assert left >= 0, (language, control.objectName())
                assert left + control.width() <= viewport.width(), (language, control.objectName())
        assert page.service.world is None
        page.create_button.setFocus()
        QTest.keyClick(page.create_button, Qt.Key.Key_Space)
        assert page.service.world is not None
    finally:
        set_language('English', window)


def test_created_home_does_not_widen_the_whole_page(make_main_window):
    window = make_main_window()
    window.resize(536, 500)
    window.show()
    page = window.pet_home_ui
    page.create_home()
    try:
        for _label, language in LANGUAGES:
            assert set_language(language, window)
            window.resize(536, 500)
            for key in page.tabs.keys():
                assert page.tabs.select(key)
                for _ in range(3):
                    QApplication.processEvents()
                assert page._scroll.horizontalScrollBar().maximum() == 0, (language, key, window.width())
                for check in page.tabs.findChildren(WrappingCheckBox):
                    if check.isVisible():
                        assert check.height() >= check.heightForWidth(check.width()), (language, key)
    finally:
        set_language('English', window)


def test_work_recovery_keeps_toolbar_below_home(make_main_window):
    from PySide6.QtCore import QRect
    from frontengine.utils.pet_game import behaviour, simulation

    window = make_main_window()
    page = window.pet_home_ui
    screen = QApplication.primaryScreen()
    area = screen.availableGeometry()
    world = page.service.create_home(screen.name() or "primary", area.x(), area.bottom(), 48, seed=5)
    world.time_ms = 0
    world.automatic = False
    zone = next(iter(world.zones))
    world.ledger.apply("fixture", "Layout regression", 500)
    pet = page.service.profiles.create("Mochi")["id"]
    page.service.profiles.update(pet, {"mood": 80, "fullness": 90, "energy": 95})
    assert page.service.adopt(pet, zone) == "accepted"
    assert world.create_task("letter", pet)[0] == "accepted"
    assert world.command(pet, "work") == "accepted"
    simulation.step(world)
    window.resize(1280, 960)
    window.show()
    page.refresh()
    page.tabs.select("pet_home_residents_section")
    page.select_resident(pet)
    QTest.qWait(200)
    before = page.pending_list.height()
    world.furnish(zone)
    behaviour.cancel_activity(world, world.residents[pet], "fixture")
    assert world.command(pet, "work") == "accepted"
    simulation.step(world)
    page.refresh()
    QTest.qWait(200)
    assert world.residents[pet].activity.kind == "work"
    assert page.pending_list.height() < before
    view = QRect(page.view_area.mapTo(page, QPoint()), page.view_area.size())
    toolbar = QRect(page.shortcuts.mapTo(page, QPoint()), page.shortcuts.size())
    assert toolbar.top() > view.bottom(), (view.getRect(), toolbar.getRect())
