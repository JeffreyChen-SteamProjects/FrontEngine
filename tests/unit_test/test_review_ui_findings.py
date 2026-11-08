"""UI defects found by the cumulative-branch review.

A saved screen-filter colour must not depend on the display language, Start/Stop
buttons must keep their running state across a language switch, the screen-text
consent prompt must not vanish because its page is behind another one, and the
weather lookup thread must not raise or write after the page retired.
"""
import re
import threading
from pathlib import Path

import pytest

from frontengine.ui.menu.language_menu import LANGUAGES
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import translate

ROOT = Path(__file__).resolve().parents[2]


def _switch(window, index):
    window.language_menu.actions()[index].trigger()


def test_saved_screen_filter_colour_survives_a_language_change(make_main_window):
    from frontengine.show.screen_care.screen_filter import FILTER_COLORS
    window = make_main_window()
    page = window.screen_care_setting_ui
    combo = page.filter_color_combobox
    combo.setCurrentIndex(combo.findData(dict(FILTER_COLORS)['Amber']))
    selected = combo.currentData()
    try:
        for index in [*range(len(LANGUAGES)), 0]:
            _switch(window, index)
            assert [combo.itemText(i) for i in range(combo.count())] == [
                translate(f"screen_filter_color_{name.lower()}", name) for name, _ in FILTER_COLORS]
            assert combo.currentData() == selected
            state = page.get_state()
            assert state['filter_color'] == 'Amber'
            combo.setCurrentIndex(0)
            page.set_state(state)
            assert combo.currentData() == selected
    finally:
        _switch(window, 0)


@pytest.mark.parametrize('language', ['Deutsch', 'Traditional_Chinese', 'Russian'])
def test_legacy_translated_filter_colour_is_still_restored(make_main_window, language):
    from frontengine.show.screen_care.screen_filter import FILTER_COLORS
    window = make_main_window()
    page = window.screen_care_setting_ui
    combo = page.filter_color_combobox
    legacy = language_wrapper.choose_language_dict[language]['screen_filter_color_rose']
    combo.setCurrentIndex(0)
    page.set_state({'filter_color': legacy})
    assert combo.currentData() == dict(FILTER_COLORS)['Rose']
    page.set_state({'filter_color': 'not a colour'})
    assert combo.currentData() == dict(FILTER_COLORS)['Rose']


def test_running_measure_button_keeps_stop_label_across_a_language_change(make_main_window):
    window = make_main_window()
    page = window.tools_setting_ui
    page.start_measure()
    try:
        for index in [*range(len(LANGUAGES)), 0]:
            _switch(window, index)
            assert page.measure_button.text() == translate("tools_measure_stop", "Stop measuring")
        page.stop_measure()
        _switch(window, 1)
        assert page.measure_button.text() == translate("tools_measure_start", "Start measuring")
    finally:
        page.stop_measure()
        _switch(window, 0)


@pytest.mark.parametrize('relative', ['frontengine/ui/page/tools/tools_setting_ui.py',
                                      'frontengine/ui/page/widgets/widgets_setting_ui.py'])
def test_start_stop_buttons_change_text_through_the_retranslator(relative):
    source = (ROOT / relative).read_text(encoding='utf-8')
    assert not re.findall(r'_button\.setText\(', source)


@pytest.mark.parametrize('kind', ['text', 'capture'])
def test_consent_is_asked_for_a_page_behind_another_page_of_a_visible_window(monkeypatch, kind):
    from PySide6.QtWidgets import QMessageBox, QStackedWidget, QWidget
    from frontengine.ui.dialog import screen_text_dialog
    key = screen_text_dialog.TEXT_CONSENT_KEY if kind == 'text' else screen_text_dialog.CONSENT_KEY
    ask = screen_text_dialog.ask_for_text_consent if kind == 'text' else screen_text_dialog.ask_for_consent
    monkeypatch.setitem(screen_text_dialog.user_setting_dict, key, False)
    monkeypatch.setattr(screen_text_dialog, 'write_user_setting', lambda: None)
    asked = []
    monkeypatch.setattr(QMessageBox, 'question', lambda *_a: asked.append(True) or QMessageBox.StandardButton.Yes)
    stack = QStackedWidget()
    tools, other = QWidget(), QWidget()
    stack.addWidget(tools)
    stack.addWidget(other)
    stack.setCurrentWidget(other)
    stack.show()
    try:
        assert not tools.isVisible() and tools.window().isVisible()
        assert ask(tools)
        assert asked == [True]
        assert screen_text_dialog.user_setting_dict[key] is True
    finally:
        stack.close()


def _resolve(page, monkeypatch, found, retire):
    from frontengine.ui.page.text import text_setting_ui as module
    from frontengine.utils.work_lifetime import RuntimeState
    located, errors = [], []

    def lookup(city):
        if retire:
            page.lifetime.state = RuntimeState.RETIRING
        return found

    monkeypatch.setattr(module, 'lookup_city', lookup)
    monkeypatch.setattr(module, 'weather_service',
                        lambda: type('S', (), {'set_location': lambda _s, *a: located.append(a)})())
    monkeypatch.setattr(threading, 'excepthook', lambda info: errors.append(info.exc_value))
    page.weather_location_edit.setText('Atlantis')
    page._weather_city_resolved = None
    try:
        page._apply_weather_location()
        for thread in threading.enumerate():
            if thread.name == 'frontengine-city-lookup':
                thread.join(5)
    finally:
        page.lifetime.state = RuntimeState.LIVE
    return located, errors


@pytest.mark.parametrize('found', [None, (25.0, 121.5)])
def test_weather_lookup_finishing_after_retirement_neither_raises_nor_writes(make_main_window, monkeypatch, found):
    page = make_main_window().text_setting_ui
    located, errors = _resolve(page, monkeypatch, found, retire=True)
    assert errors == []
    assert located == []


def test_weather_lookup_while_live_still_sets_the_location(make_main_window, monkeypatch):
    page = make_main_window().text_setting_ui
    located, errors = _resolve(page, monkeypatch, (25.0, 121.5), retire=False)
    assert errors == []
    assert located == [(25.0, 121.5)]
