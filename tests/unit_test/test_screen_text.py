"""
把截圖交給 Claude 讀取文字的測試。重點在「沒有同意就什麼都不送」——
這是本專案唯一會把畫面內容送出機器的功能，所以那道閘門要有測試守著。

Tests for handing a capture to Claude. The point of most of them is that
nothing is sent without consent: this is the only feature here that puts screen
content on the wire, so the gate needs tests holding it shut.
"""
import base64

from frontengine.utils.screen_text.screen_text_service import (
    ACTION_ASK, ACTION_EXTRACT, ACTION_TRANSLATE, API_KEY_ENV, DEFAULT_LANGUAGE, ScreenTextService,
    api_key, build_message, image_block, normalize_action, prompt_for, reply_text,
)

PNG = b"\x89PNG\r\n\x1a\n fake bytes"


class FakeBlock:
    def __init__(self, text):
        self.text = text


class FakeResponse:
    def __init__(self, blocks, stop_reason="end_turn"):
        self.content = blocks
        self.stop_reason = stop_reason


# --- actions and prompts --------------------------------------------------
def test_an_unknown_action_falls_back_to_copying_text() -> None:
    assert normalize_action("nonsense") == ACTION_EXTRACT
    assert normalize_action(None) == ACTION_EXTRACT
    assert normalize_action("TRANSLATE") == ACTION_TRANSLATE


def test_the_extract_prompt_asks_for_a_bare_transcription() -> None:
    prompt = prompt_for(ACTION_EXTRACT)
    assert "Transcribe" in prompt and "(no text)" in prompt


def test_the_translate_prompt_names_the_target_language() -> None:
    assert "Japanese" in prompt_for(ACTION_TRANSLATE, "Japanese")


def test_a_blank_language_falls_back_to_the_default() -> None:
    assert DEFAULT_LANGUAGE in prompt_for(ACTION_TRANSLATE, "   ")


def test_asking_uses_the_question_verbatim() -> None:
    assert prompt_for(ACTION_ASK, question="What error is this?") == "What error is this?"


def test_asking_nothing_becomes_a_transcription() -> None:
    # 送一張圖卻不問任何事沒有意義，所以退回成取出文字
    assert "Transcribe" in prompt_for(ACTION_ASK, question="   ")


# --- request shape --------------------------------------------------------
def test_the_image_is_sent_as_base64_png() -> None:
    block = image_block(PNG)
    assert block["type"] == "image"
    assert block["source"]["media_type"] == "image/png"
    assert base64.standard_b64decode(block["source"]["data"]) == PNG


def test_no_image_means_no_block_and_no_message() -> None:
    assert image_block(b"") is None
    assert build_message(b"", ACTION_EXTRACT) is None


def test_the_message_carries_the_image_and_the_instruction() -> None:
    messages = build_message(PNG, ACTION_TRANSLATE, "German")
    assert len(messages) == 1 and messages[0]["role"] == "user"
    kinds = [part["type"] for part in messages[0]["content"]]
    assert kinds == ["image", "text"]
    assert "German" in messages[0]["content"][1]["text"]


# --- responses ------------------------------------------------------------
def test_text_blocks_are_joined() -> None:
    assert reply_text(FakeResponse([FakeBlock("one"), FakeBlock("two")])) == "one\ntwo"


def test_a_refusal_is_reported_as_no_answer() -> None:
    assert reply_text(FakeResponse([FakeBlock("...")], stop_reason="refusal")) is None


def test_an_empty_response_is_no_answer() -> None:
    assert reply_text(FakeResponse([])) is None
    assert reply_text(FakeResponse([FakeBlock("   ")])) is None
    assert reply_text(None) is None


# --- the consent gate -----------------------------------------------------
def test_without_consent_nothing_is_sent() -> None:
    sent = []

    class Boom:
        class messages:
            @staticmethod
            def create(**kwargs):
                sent.append(kwargs)
                raise AssertionError("must not be called without consent")

    service = ScreenTextService(consent_provider=lambda: False,
                                key_provider=lambda: "test-key")
    service._client = Boom()
    assert service.read(PNG, ACTION_EXTRACT) is None
    assert sent == []


def test_without_a_key_the_feature_is_unavailable() -> None:
    service = ScreenTextService(consent_provider=lambda: True, key_provider=lambda: None)
    assert service.available() is False
    assert service.read(PNG) is None


def test_consent_alone_is_not_enough_and_neither_is_a_key() -> None:
    assert ScreenTextService(consent_provider=lambda: True,
                             key_provider=lambda: "k").available() is True
    assert ScreenTextService(consent_provider=lambda: False,
                             key_provider=lambda: "k").available() is False


def test_a_failing_consent_check_counts_as_refusal() -> None:
    def boom():
        raise RuntimeError("settings unreadable")

    service = ScreenTextService(consent_provider=boom, key_provider=lambda: "k")
    assert service.consented() is False
    assert service.read(PNG) is None


def test_an_empty_capture_is_never_sent() -> None:
    sent = []

    class Recorder:
        class messages:
            @staticmethod
            def create(**kwargs):
                sent.append(kwargs)
                return FakeResponse([FakeBlock("hi")])

    service = ScreenTextService(consent_provider=lambda: True, key_provider=lambda: "k")
    service._client = Recorder()
    assert service.read(b"", ACTION_EXTRACT) is None
    assert sent == []


def test_a_granted_request_carries_the_capture_and_the_model() -> None:
    sent = []

    class Recorder:
        class messages:
            @staticmethod
            def create(**kwargs):
                sent.append(kwargs)
                return FakeResponse([FakeBlock("hello world")])

    service = ScreenTextService(consent_provider=lambda: True, key_provider=lambda: "k")
    service._client = Recorder()
    assert service.read(PNG, ACTION_EXTRACT) == "hello world"
    assert len(sent) == 1
    assert sent[0]["model"] == service.model
    assert sent[0]["messages"][0]["content"][0]["type"] == "image"


def test_a_failing_request_is_reported_as_no_answer() -> None:
    class Broken:
        class messages:
            @staticmethod
            def create(**kwargs):
                raise RuntimeError("network down")

    service = ScreenTextService(consent_provider=lambda: True, key_provider=lambda: "k")
    service._client = Broken()
    assert service.read(PNG) is None


# --- key handling ---------------------------------------------------------
def test_the_key_comes_from_the_environment_only() -> None:
    assert api_key({API_KEY_ENV: " secret "}) == "secret"
    assert api_key({}) is None
    assert api_key({API_KEY_ENV: "   "}) is None
