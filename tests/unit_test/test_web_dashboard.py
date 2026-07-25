"""
網頁儀表板的純邏輯測試：網址清單解析與換頁索引。
Pure-logic tests for the web dashboard: URL list parsing and page cycling.
"""
from frontengine.user_setting.user_setting_file import default_hotkeys
from frontengine.utils.web_url import next_page_index, parse_dashboard_urls


def test_one_url_per_line() -> None:
    text = "https://a.example\nhttps://b.example"
    assert parse_dashboard_urls(text) == ["https://a.example", "https://b.example"]


def test_blank_lines_and_comments_are_dropped() -> None:
    text = "\n  https://a.example  \n\n# a note\n\thttps://b.example\n"
    assert parse_dashboard_urls(text) == ["https://a.example", "https://b.example"]


def test_empty_and_bad_input() -> None:
    assert parse_dashboard_urls("") == []
    assert parse_dashboard_urls("   \n\n# only comments") == []
    assert parse_dashboard_urls(None) == []


def test_next_page_wraps() -> None:
    assert next_page_index(0, 3) == 1
    assert next_page_index(2, 3) == 0, "the last page wraps to the first"
    assert next_page_index(0, 3, step=-1) == 2, "stepping back wraps too"


def test_next_page_with_no_pages() -> None:
    assert next_page_index(0, 0) == 0
    assert next_page_index(5, 0) == 0
    assert next_page_index("x", 3) == 0


def test_dashboard_has_a_default_hotkey() -> None:
    assert default_hotkeys.get("dashboard_next")
