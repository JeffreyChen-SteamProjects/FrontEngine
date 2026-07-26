"""
準星、提詞機、音效板與 OBS 協定的純邏輯測試。

OBS 那部分特別值得測：認證字串是照文件寫死的算法，而 WebSocket 訊框
自己實作就得自己證明它編得對、解得回來。

Tests for the crosshair, teleprompter, soundboard and the OBS protocol.

The OBS half is the one that earns its tests: the authentication string follows
a fixed documented algorithm, and hand-rolled WebSocket framing has to prove it
encodes and decodes correctly.
"""
import base64
import hashlib
import json

from frontengine.show.gaming.crosshair_widget import (
    MAX_SIZE, MIN_SIZE, STYLE_CIRCLE, STYLE_CROSS, STYLE_DOT, arm_segments, clamp_gap, clamp_size,
    clamp_thickness, normalize_style,
)
from frontengine.show.teleprompter.teleprompter_widget import (
    MAX_SPEED, MIN_SPEED, clamp_font_size, clamp_speed, wrap_lines,
)
from frontengine.utils.obs.obs_protocol import (
    OP_IDENTIFY, OP_REQUEST, authentication_string, decode, encode, hello_needs_auth,
    identify_message, is_identified, recording_request, response_comment, response_status,
    scene_request, streaming_request,
)
from frontengine.utils.obs.websocket_frames import (
    OPCODE_PING, OPCODE_TEXT, accept_key, decode_frame, encode_frame, handshake_request,
    handshake_succeeded,
)
from frontengine.utils.soundboard.soundboard import (
    MAX_SLOTS, Soundboard, clamp_volume, hotkey_bindings, normalize_slot, normalize_slots,
    slot_index_for_action,
)


def make_sound(tmp_path, name="beep.wav"):
    path = tmp_path / name
    path.write_bytes(b"RIFF....WAVEfmt ")
    return str(path)


# --- crosshair ------------------------------------------------------------
def test_an_unknown_crosshair_style_falls_back_to_a_cross() -> None:
    assert normalize_style("laser") == STYLE_CROSS
    assert normalize_style("DOT") == STYLE_DOT
    assert normalize_style(None) == STYLE_CROSS
    assert normalize_style(STYLE_CIRCLE) == STYLE_CIRCLE


def test_the_crosshair_size_stays_usable() -> None:
    assert clamp_size(0) == MIN_SIZE
    assert clamp_size(10 ** 6) == MAX_SIZE
    assert clamp_size("nonsense") == 24


def test_the_line_stays_thick_enough_to_see() -> None:
    assert clamp_thickness(0) == 1
    assert clamp_thickness(100) == 12
    assert clamp_thickness(None) == 2


def test_the_centre_gap_cannot_swallow_the_crosshair() -> None:
    assert clamp_gap(500, size=20) == 19
    assert clamp_gap(-5, size=20) == 0
    assert clamp_gap(6, size=20) == 6


def test_arms_start_after_the_gap_and_end_at_the_size() -> None:
    assert arm_segments(20, 6) == ((6, 20),)


def test_the_gap_can_never_swallow_the_crosshair() -> None:
    # 空隙被夾在尺寸之內，所以手臂一定還剩至少一個像素
    inner, outer = arm_segments(8, 8)[0]
    assert inner < outer


# --- teleprompter ---------------------------------------------------------
def test_the_scroll_speed_is_clamped() -> None:
    assert clamp_speed(0) == MIN_SPEED
    assert clamp_speed(10 ** 6) == MAX_SPEED
    assert clamp_speed("nonsense") == 40


def test_the_prompter_font_stays_readable() -> None:
    assert clamp_font_size(1) == 10
    assert clamp_font_size(500) == 120


def test_wrapping_keeps_blank_lines_as_pauses() -> None:
    class Metrics:
        @staticmethod
        def horizontalAdvance(text):
            return len(text) * 10

    lines = wrap_lines("first paragraph\n\nsecond", Metrics(), 200)
    assert lines[1] == ""
    assert lines[0] == "first paragraph" and lines[-1] == "second"


def test_a_long_line_is_wrapped_to_the_width() -> None:
    class Metrics:
        @staticmethod
        def horizontalAdvance(text):
            return len(text) * 10

    lines = wrap_lines("one two three four five", Metrics(), 100)
    assert len(lines) > 1
    assert all(len(line) <= 10 for line in lines)


def test_an_empty_script_wraps_to_nothing() -> None:
    class Metrics:
        @staticmethod
        def horizontalAdvance(text):
            return len(text)

    assert wrap_lines("", Metrics(), 100) == []


# --- soundboard -----------------------------------------------------------
def test_a_sound_that_is_not_there_is_refused(tmp_path) -> None:
    assert normalize_slot({"path": str(tmp_path / "missing.wav")}) is None
    assert normalize_slot({"path": ""}) is None
    assert normalize_slot("not a slot") is None


def test_a_file_that_is_not_a_sound_is_refused(tmp_path) -> None:
    document = tmp_path / "notes.txt"
    document.write_text("hello", encoding="utf-8")
    assert normalize_slot({"path": str(document)}) is None


def test_a_blank_label_falls_back_to_the_file_name(tmp_path) -> None:
    slot = normalize_slot({"path": make_sound(tmp_path)})
    assert slot["label"] == "beep"


def test_an_invalid_hotkey_is_dropped_rather_than_kept(tmp_path) -> None:
    slot = normalize_slot({"path": make_sound(tmp_path), "hotkey": "not a combo"})
    assert slot["hotkey"] == ""


def test_a_valid_hotkey_survives(tmp_path) -> None:
    slot = normalize_slot({"path": make_sound(tmp_path), "hotkey": "<ctrl>+<shift>+1"})
    assert slot["hotkey"] == "<ctrl>+<shift>+1"


def test_the_volume_is_clamped() -> None:
    assert clamp_volume(-1) == 0.0
    assert clamp_volume(5) == 1.0
    assert clamp_volume("nonsense") == 1.0


def test_more_slots_than_the_board_holds_are_dropped(tmp_path) -> None:
    slots = [{"path": make_sound(tmp_path, f"s{index}.wav")} for index in range(MAX_SLOTS + 5)]
    assert len(normalize_slots(slots)) == MAX_SLOTS


def test_hotkey_actions_are_namespaced(tmp_path) -> None:
    slots = [{"path": make_sound(tmp_path, "a.wav"), "hotkey": "<ctrl>+1"},
             {"path": make_sound(tmp_path, "b.wav")}]
    assert hotkey_bindings(slots) == {"soundboard:0": "<ctrl>+1"}


def test_an_action_name_maps_back_to_its_slot() -> None:
    assert slot_index_for_action("soundboard:3") == 3
    assert slot_index_for_action("close_all") is None
    assert slot_index_for_action("soundboard:x") is None
    assert slot_index_for_action(None) is None


def test_the_board_refuses_to_grow_past_its_limit(tmp_path) -> None:
    board = Soundboard()
    for index in range(MAX_SLOTS):
        assert board.add(make_sound(tmp_path, f"s{index}.wav")) is not None
    assert board.add(make_sound(tmp_path, "one_too_many.wav")) is None


def test_playing_a_slot_that_is_not_there_fails_quietly(tmp_path) -> None:
    board = Soundboard()
    assert board.play(0) is False
    assert board.play_action("soundboard:9") is False
    assert board.remove(4) is False


# --- OBS authentication ---------------------------------------------------
def test_the_authentication_string_matches_the_documented_algorithm() -> None:
    password, salt, challenge = "secret", "saltysalt", "chall3nge"
    secret = base64.b64encode(hashlib.sha256((password + salt).encode()).digest()).decode()
    expected = base64.b64encode(hashlib.sha256((secret + challenge).encode()).digest()).decode()
    assert authentication_string(password, salt, challenge) == expected


def test_a_hello_without_authentication_needs_no_password() -> None:
    hello = {"op": 0, "d": {"rpcVersion": 1}}
    assert hello_needs_auth(hello) is False
    message = identify_message(hello)
    assert message["op"] == OP_IDENTIFY and "authentication" not in message["d"]


def test_a_hello_with_authentication_and_no_password_is_refused() -> None:
    hello = {"op": 0, "d": {"authentication": {"salt": "s", "challenge": "c"}}}
    assert hello_needs_auth(hello) is True
    assert identify_message(hello, "") is None


def test_a_hello_with_a_password_carries_the_authentication_string() -> None:
    hello = {"op": 0, "d": {"authentication": {"salt": "s", "challenge": "c"}}}
    message = identify_message(hello, "pw")
    assert message["d"]["authentication"] == authentication_string("pw", "s", "c")


def test_something_that_is_not_a_hello_is_ignored() -> None:
    assert identify_message({"op": 5}) is None
    assert identify_message("hello") is None


# --- OBS requests and responses -------------------------------------------
def test_switching_a_scene_names_the_scene() -> None:
    message = scene_request("Starting Soon")
    assert message["op"] == OP_REQUEST
    assert message["d"]["requestType"] == "SetCurrentProgramScene"
    assert message["d"]["requestData"]["sceneName"] == "Starting Soon"


def test_recording_and_streaming_have_start_and_stop_forms() -> None:
    assert recording_request(True)["d"]["requestType"] == "StartRecord"
    assert recording_request(False)["d"]["requestType"] == "StopRecord"
    assert streaming_request(True)["d"]["requestType"] == "StartStream"
    assert streaming_request(False)["d"]["requestType"] == "StopStream"


def test_a_successful_response_reads_as_success() -> None:
    message = {"op": 7, "d": {"requestStatus": {"result": True, "code": 100}}}
    assert response_status(message) is True
    assert response_comment(message) == ""


def test_a_failed_response_carries_the_reason() -> None:
    message = {"op": 7, "d": {"requestStatus": {"result": False, "comment": "no such scene"}}}
    assert response_status(message) is False
    assert response_comment(message) == "no such scene"


def test_other_messages_are_not_responses() -> None:
    assert response_status({"op": 5}) is None
    assert response_status("nonsense") is None
    assert is_identified({"op": 2}) is True
    assert is_identified({"op": 0}) is False


def test_messages_round_trip_through_json() -> None:
    message = scene_request("Break")
    assert decode(encode(message)) == message
    assert decode("not json") is None
    assert decode("[1, 2]") is None


# --- WebSocket framing ----------------------------------------------------
def test_the_handshake_asks_for_an_upgrade() -> None:
    request = handshake_request("127.0.0.1", 4455, "abc123").decode()
    assert request.startswith("GET / HTTP/1.1")
    assert "Upgrade: websocket" in request and "Sec-WebSocket-Key: abc123" in request


def test_the_accept_key_follows_the_rfc() -> None:
    # RFC 6455 的範例：這個 key 對應到這個 accept
    assert accept_key("dGhlIHNhbXBsZSBub25jZQ==") == "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="


def test_a_correct_handshake_response_is_accepted() -> None:
    key = "dGhlIHNhbXBsZSBub25jZQ=="
    response = ("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n"
                f"Sec-WebSocket-Accept: {accept_key(key)}\r\n\r\n").encode()
    assert handshake_succeeded(response, key) is True


def test_a_wrong_accept_or_status_is_rejected() -> None:
    key = "dGhlIHNhbXBsZSBub25jZQ=="
    wrong_accept = ("HTTP/1.1 101 Switching Protocols\r\n"
                    "Sec-WebSocket-Accept: nonsense\r\n\r\n").encode()
    wrong_status = ("HTTP/1.1 400 Bad Request\r\n"
                    f"Sec-WebSocket-Accept: {accept_key(key)}\r\n\r\n").encode()
    assert handshake_succeeded(wrong_accept, key) is False
    assert handshake_succeeded(wrong_status, key) is False
    assert handshake_succeeded(b"", key) is False


def test_a_client_frame_is_always_masked() -> None:
    frame = encode_frame(b"hello")
    assert frame[0] == 0x81                 # FIN + text
    assert frame[1] & 0x80                  # mask bit set


def test_a_frame_decodes_back_to_what_went_in() -> None:
    payload = b"the quick brown fox"
    opcode, decoded, used = decode_frame(encode_frame(payload))
    assert opcode == OPCODE_TEXT and decoded == payload
    assert used == len(encode_frame(payload))


def test_a_medium_payload_uses_the_extended_length() -> None:
    payload = b"x" * 300
    opcode, decoded, _used = decode_frame(encode_frame(payload))
    assert opcode == OPCODE_TEXT and decoded == payload


def test_a_large_payload_uses_the_long_length() -> None:
    payload = b"y" * 70000
    opcode, decoded, _used = decode_frame(encode_frame(payload))
    assert opcode == OPCODE_TEXT and decoded == payload


def test_a_partial_frame_asks_for_more_data() -> None:
    frame = encode_frame(b"a longer message than this slice")
    assert decode_frame(frame[:4]) == (None, None, 0)
    assert decode_frame(b"") == (None, None, 0)


def test_two_frames_in_one_buffer_are_read_one_at_a_time() -> None:
    buffer = encode_frame(b"first") + encode_frame(b"second")
    opcode, payload, used = decode_frame(buffer)
    assert payload == b"first"
    opcode, payload, _used = decode_frame(buffer[used:])
    assert payload == b"second"


def test_a_control_frame_keeps_its_opcode() -> None:
    opcode, payload, _used = decode_frame(encode_frame(b"", OPCODE_PING))
    assert opcode == OPCODE_PING and payload == b""


def test_the_encoded_message_is_compact_json() -> None:
    assert encode({"op": 6}) == json.dumps({"op": 6}, separators=(",", ":"))
