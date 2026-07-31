"""
第一次啟動跟著 Steam 語言走的規則。

這裡最要緊的不是「有沒有讀到 Steam 語言」，而是**讀到之後什麼時候可以用**：
使用者挑過語言之後就不能再被蓋掉，否則選單改了語言、下次開啟又變回去，
使用者看到的是一個壞掉的選單。

The first-launch Steam language rule. What matters here is less "can it read the
Steam language" than *when it is allowed to win*: once the user has chosen, it
must not be overridden, or changing the language in the menu silently reverts on
the next launch and the menu looks broken.
"""
import json
import os

import pytest

from frontengine.user_setting.user_setting_file import is_stored, user_setting_dict
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.steam import steam_language as steam_module
from frontengine.utils.steam.steam_language import (
    STEAM_LANGUAGE_MAP, _vdf_language_code, steam_language,
)


@pytest.fixture
def in_tmp_dir(tmp_path):
    """設定檔是相對於工作目錄找的，所以測試要換過去。"""
    original = os.getcwd()
    os.chdir(tmp_path)
    try:
        yield tmp_path
    finally:
        os.chdir(original)


def test_every_mapped_name_is_a_language_the_app_registers():
    """
    對應表指到的名稱必須是 reset_language() 認得的。打錯字的話語言不會切換，
    而且完全沒有痕跡——這正是這張表最容易壞掉的方式。
    """
    for code, name in STEAM_LANGUAGE_MAP.items():
        assert name in language_wrapper.choose_language_dict, f"{code} -> {name} is not registered"


def test_the_seven_codes_map_to_the_seven_languages():
    assert STEAM_LANGUAGE_MAP["tchinese"] == "Traditional_Chinese"
    assert STEAM_LANGUAGE_MAP["schinese"] == "Simplified_Chinese"
    assert STEAM_LANGUAGE_MAP["german"] == "Deutsch"
    assert STEAM_LANGUAGE_MAP["french"] == "France"
    assert STEAM_LANGUAGE_MAP["italian"] == "Italy"
    assert STEAM_LANGUAGE_MAP["russian"] == "Russian"
    assert STEAM_LANGUAGE_MAP["english"] == "English"


def test_a_language_we_have_no_translation_for_is_not_forced(monkeypatch):
    """Steam 設成日文時要回傳 None，維持預設，而不是硬選一個。"""
    monkeypatch.setattr(steam_module, "steam_language_code", lambda: "japanese")
    assert steam_language() is None


def test_no_steam_means_no_opinion(monkeypatch):
    monkeypatch.setattr(steam_module, "steam_language_code", lambda: None)
    assert steam_language() is None


def test_registry_vdf_is_read_on_the_platforms_without_a_registry(tmp_path):
    """macOS 與 Linux 沒有 winreg，語言在 Steam 自己的 registry.vdf 裡。"""
    vdf = tmp_path / "registry.vdf"
    vdf.write_text(
        '"Registry"\n{\n\t"HKCU"\n\t{\n\t\t"Software"\n\t\t{\n'
        '\t\t\t"Valve"\n\t\t\t{\n\t\t\t\t"Steam"\n\t\t\t\t{\n'
        '\t\t\t\t\t"Language"\t\t"german"\n'
        '\t\t\t\t}\n\t\t\t}\n\t\t}\n\t}\n}\n',
        encoding="utf-8")
    assert _vdf_language_code([vdf]) == "german"


def test_a_missing_vdf_is_not_an_error(tmp_path):
    assert _vdf_language_code([tmp_path / "nope.vdf"]) is None


def test_first_launch_follows_steam_and_records_it(in_tmp_dir, monkeypatch):
    """
    設定檔裡還沒有 language：跟著 Steam，並把結果寫進設定，
    這樣同一件事只會發生一次。
    """
    from frontengine.ui.main_ui import FrontEngineMainUI

    monkeypatch.setattr("frontengine.ui.main_ui.steam_language", lambda: "Deutsch")
    (in_tmp_dir / "user_setting.json").write_text(json.dumps({"theme": "dark_amber.xml"}),
                                                  encoding="utf-8")
    user_setting_dict["language"] = "English"

    assert is_stored("language") is False
    assert FrontEngineMainUI._startup_language() == "Deutsch"
    assert user_setting_dict["language"] == "Deutsch"


def test_a_language_the_user_chose_is_never_overridden(in_tmp_dir, monkeypatch):
    """
    使用者挑過（設定檔裡有 language）：Steam 說什麼都不算。
    少了這條，選單裡改語言下次開啟就會被改回去。
    """
    from frontengine.ui.main_ui import FrontEngineMainUI

    monkeypatch.setattr("frontengine.ui.main_ui.steam_language", lambda: "Deutsch")
    (in_tmp_dir / "user_setting.json").write_text(json.dumps({"language": "Italy"}),
                                                  encoding="utf-8")
    user_setting_dict["language"] = "Italy"

    assert is_stored("language") is True
    assert FrontEngineMainUI._startup_language() == "Italy"
    assert user_setting_dict["language"] == "Italy"


def test_choosing_english_counts_as_choosing(in_tmp_dir, monkeypatch):
    """
    「使用者選了英文」和「使用者沒選過」不一樣。合併預設值之後兩者長得一模一樣，
    所以這件事得問檔案本身——這條測試就是釘住那個區別。
    """
    from frontengine.ui.main_ui import FrontEngineMainUI

    monkeypatch.setattr("frontengine.ui.main_ui.steam_language", lambda: "Traditional_Chinese")
    (in_tmp_dir / "user_setting.json").write_text(json.dumps({"language": "English"}),
                                                  encoding="utf-8")
    user_setting_dict["language"] = "English"

    assert FrontEngineMainUI._startup_language() == "English"


def test_no_settings_file_at_all_still_follows_steam(in_tmp_dir, monkeypatch):
    from frontengine.ui.main_ui import FrontEngineMainUI

    monkeypatch.setattr("frontengine.ui.main_ui.steam_language", lambda: "Russian")
    user_setting_dict["language"] = "English"

    assert is_stored("language") is False
    assert FrontEngineMainUI._startup_language() == "Russian"


def test_without_steam_the_stored_default_is_kept(in_tmp_dir, monkeypatch):
    from frontengine.ui.main_ui import FrontEngineMainUI

    monkeypatch.setattr("frontengine.ui.main_ui.steam_language", lambda: None)
    user_setting_dict["language"] = "English"

    assert FrontEngineMainUI._startup_language() == "English"
