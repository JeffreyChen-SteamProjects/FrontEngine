"""
手機遙控與 MIDI 的純邏輯測試。遙控會在機器上開網路埠，所以權杖與動作
白名單這兩道關卡要有測試守著。

Tests for the phone remote and MIDI. The remote opens a port on the machine, so
the two gates - the token and the action allowlist - need tests holding them.
"""
from frontengine.utils.midi.midi_input import (
    CONTROL_CHANGE, KIND_CONTROL, NOTE_OFF, NOTE_ON, MidiInput, available,
    binding_key, parse_message, scaled_value,
)
from frontengine.utils.remote.remote_server import (
    ALLOWED_ACTIONS, RemoteServer, is_allowed, local_address, make_token, parse_request,
    remote_url,
)


def packed(status: int, data1: int = 0, data2: int = 0) -> int:
    return status | (data1 << 8) | (data2 << 16)


# --- MIDI parsing ---------------------------------------------------------
def test_a_knob_turn_is_read_as_a_control_change() -> None:
    message = parse_message(packed(CONTROL_CHANGE, 7, 100))
    assert message == {"kind": KIND_CONTROL, "channel": 0, "number": 7, "value": 100}


def test_a_pad_press_and_release() -> None:
    assert parse_message(packed(NOTE_ON, 36, 127))["pressed"] is True
    assert parse_message(packed(NOTE_OFF, 36, 64))["pressed"] is False


def test_a_note_on_with_no_velocity_means_release() -> None:
    """規範上力度 0 的 note-on 等同 note-off；不照做的話放開會被當成又按一次。"""
    assert parse_message(packed(NOTE_ON, 36, 0))["pressed"] is False


def test_the_channel_is_reported() -> None:
    assert parse_message(packed(CONTROL_CHANGE | 3, 7, 1))["channel"] == 3


def test_anything_else_is_ignored() -> None:
    assert parse_message(0xF0) is None
    assert parse_message("nonsense") is None
    assert parse_message(None) is None


def test_a_binding_survives_a_channel_change() -> None:
    """多數控制器可以整台換頻道，綁定不該因此失效。"""
    on_channel_zero = binding_key(parse_message(packed(CONTROL_CHANGE, 7)))
    on_channel_five = binding_key(parse_message(packed(CONTROL_CHANGE | 5, 7)))
    assert on_channel_zero == on_channel_five == "control:7"


def test_binding_keys_separate_notes_from_knobs() -> None:
    assert binding_key(parse_message(packed(NOTE_ON, 7, 1))) != \
        binding_key(parse_message(packed(CONTROL_CHANGE, 7, 1)))


def test_values_scale_onto_a_range() -> None:
    assert scaled_value(0) == 0.0
    assert scaled_value(127) == 1.0
    assert scaled_value(999) == 1.0
    assert scaled_value(None) == 0.0
    assert scaled_value(127, 0.2, 0.8) == 0.8


def test_midi_availability_is_a_bool() -> None:
    assert isinstance(available(), bool)


def test_messages_reach_the_callback_and_a_failing_one_is_survivable() -> None:
    seen = []
    MidiInput(on_message=seen.append).handle_raw(packed(CONTROL_CHANGE, 10, 64))
    assert len(seen) == 1

    def boom(_message):
        raise RuntimeError("handler blew up")

    assert MidiInput(on_message=boom).handle_raw(packed(CONTROL_CHANGE)) is not None


def test_stopping_an_unopened_input_is_safe() -> None:
    midi = MidiInput()
    midi.stop()
    assert midi.running is False


# --- the remote's two gates ----------------------------------------------
def test_every_start_mints_a_different_token() -> None:
    first, second = make_token(), make_token()
    assert first != second


def test_only_the_listed_actions_are_allowed() -> None:
    assert is_allowed("hide_all") is True
    assert is_allowed("rm -rf /") is False
    assert is_allowed("") is False
    assert is_allowed(None) is False


def test_a_wrong_token_is_refused_and_nothing_runs() -> None:
    performed = []
    server = RemoteServer(on_action=performed.append)
    assert server.perform("not-the-token", "hide_all") == 403
    assert performed == []


def test_an_action_outside_the_list_is_refused() -> None:
    performed = []
    server = RemoteServer(on_action=performed.append)
    assert server.perform(server.token, "format_disk") == 400
    assert performed == []


def test_the_right_token_and_action_go_through() -> None:
    performed = []
    server = RemoteServer(on_action=performed.append)
    assert server.perform(server.token, "hide_all") == 200
    assert performed == ["hide_all"]


def test_the_remote_is_not_listening_until_started() -> None:
    assert RemoteServer().running is False


def test_the_link_carries_the_token() -> None:
    url = remote_url("192.168.0.5", 8770, "abc")
    assert url.startswith("http://192.168.0.5:8770/") and "token=abc" in url


def test_requests_are_split_into_path_and_query() -> None:
    assert parse_request("/action?token=a&name=hide_all") == \
        ("/action", {"token": "a", "name": "hide_all"})
    assert parse_request("/") == ("/", {})
    assert parse_request(None) == ("/", {})


def test_the_address_is_something_usable() -> None:
    address = local_address()
    assert isinstance(address, str) and address.count(".") == 3


def test_the_action_list_matches_the_hotkey_actions() -> None:
    """遙控做得到的事情，就是使用者本來按快速鍵做得到的事情。"""
    from frontengine.user_setting.user_setting_file import default_hotkeys

    assert set(ALLOWED_ACTIONS) <= set(default_hotkeys)
