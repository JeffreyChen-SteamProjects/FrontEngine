"""
寵物 AI 對話的測試：全部用假的 client，不連網路、不需要金鑰，也驗證沒有金鑰時
功能會安靜停用、金鑰不會被寫進任何設定。

Tests for the pet's AI chat: everything runs against a fake client, so no
network and no key are needed. Also checks the feature disables itself without
a key and that the key is never persisted anywhere.
"""
import pytest

from frontengine.user_setting.user_setting_file import user_setting_dict
from frontengine.utils.pet_chat.pet_chat_service import (
    API_KEY_ENV, DEFAULT_PERSONA, HISTORY_LIMIT, MODEL, PetChatService, api_key, reply_text,
    trim_history,
)


class Block:
    def __init__(self, text: str, type: str = "text") -> None:
        self.text = text
        self.type = type


class Response:
    def __init__(self, blocks, stop_reason: str = "end_turn") -> None:
        self.content = blocks
        self.stop_reason = stop_reason


class FakeMessages:
    def __init__(self, response=None, error=None) -> None:
        self.response = response
        self.error = error
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


class FakeClient:
    def __init__(self, response=None, error=None) -> None:
        self.messages = FakeMessages(response, error)


def service_with(response=None, error=None) -> PetChatService:
    client = FakeClient(response, error)
    return PetChatService(client_factory=lambda: client)


# --- key handling ---------------------------------------------------------
def test_key_comes_from_the_environment_only() -> None:
    assert api_key({API_KEY_ENV: "sk-test"}) == "sk-test"
    assert api_key({API_KEY_ENV: "  "}) is None
    assert api_key({}) is None


def test_no_key_means_unavailable() -> None:
    service = PetChatService(key_provider=lambda: None)
    assert service.available() is False
    assert service.ask("hello") is None, "an unusable service must not raise"


def test_a_key_makes_it_available() -> None:
    assert PetChatService(key_provider=lambda: "sk-test").available() is True


def test_the_key_is_never_written_to_settings() -> None:
    PetChatService(key_provider=lambda: "sk-secret").available()
    serialised = repr(user_setting_dict)
    assert "sk-secret" not in serialised
    assert not any("api_key" in str(key).lower() for key in user_setting_dict)


# --- history --------------------------------------------------------------
def test_history_is_trimmed_and_starts_with_a_user_turn() -> None:
    history = [{"role": "user", "content": f"q{i}"} for i in range(20)]
    trimmed = trim_history(history, limit=4)
    assert len(trimmed) == 4
    assert trimmed[0]["role"] == "user"


def test_history_drops_a_leading_assistant_turn() -> None:
    history = [{"role": "assistant", "content": "a"}, {"role": "user", "content": "b"}]
    assert trim_history(history, limit=2)[0]["role"] == "user"


def test_history_drops_empty_turns() -> None:
    history = [{"role": "user", "content": ""}, {"role": "user", "content": "real"}]
    assert trim_history(history) == [{"role": "user", "content": "real"}]


# --- reply parsing --------------------------------------------------------
def test_reply_text_reads_the_first_text_block() -> None:
    assert reply_text(Response([Block("", "thinking"), Block("Hi!")])) == "Hi!"


def test_a_refusal_yields_no_reply() -> None:
    assert reply_text(Response([Block("...")], stop_reason="refusal")) is None


def test_missing_or_empty_content_yields_no_reply() -> None:
    assert reply_text(Response([])) is None
    assert reply_text(Response([Block("   ")])) is None
    assert reply_text(None) is None


# --- asking ---------------------------------------------------------------
def test_ask_returns_the_reply_and_records_the_turn() -> None:
    service = service_with(Response([Block("Woof!")]))
    assert service.ask("hello") == "Woof!"
    assert service.history[-2:] == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "Woof!"},
    ]


def test_request_uses_the_configured_model_and_short_replies() -> None:
    client = FakeClient(Response([Block("ok")]))
    service = PetChatService(client_factory=lambda: client)
    service.ask("hi")
    sent = client.messages.calls[0]
    assert sent["model"] == MODEL
    assert sent["system"] == DEFAULT_PERSONA
    assert sent["max_tokens"] <= 500, "a speech bubble only needs a short answer"
    assert sent["messages"][-1] == {"role": "user", "content": "hi"}


def test_blank_messages_are_not_sent() -> None:
    client = FakeClient(Response([Block("ok")]))
    service = PetChatService(client_factory=lambda: client)
    assert service.ask("   ") is None
    assert client.messages.calls == []


def test_a_failing_request_degrades_quietly() -> None:
    service = service_with(error=RuntimeError("network down"))
    assert service.ask("hello") is None


def test_a_refused_request_yields_no_reply_and_no_assistant_turn() -> None:
    service = service_with(Response([Block("...")], stop_reason="refusal"))
    assert service.ask("hello") is None
    assert all(turn["role"] != "assistant" for turn in service.history)


def test_history_stays_bounded_over_many_turns() -> None:
    service = service_with(Response([Block("ok")]))
    for index in range(30):
        service.ask(f"question {index}")
    assert len(service.history) <= HISTORY_LIMIT


def test_reset_forgets_the_conversation() -> None:
    service = service_with(Response([Block("ok")]))
    service.ask("hello")
    service.reset()
    assert service.history == []


def test_ask_async_delivers_the_reply(monkeypatch) -> None:
    service = service_with(Response([Block("async hi")]))
    replies = []
    started = []

    class ImmediateThread:
        def __init__(self, target=None, **_kwargs):
            self._target = target
            started.append(self)

        def start(self):
            self._target()

    monkeypatch.setattr("frontengine.utils.pet_chat.pet_chat_service.threading.Thread", ImmediateThread)
    service.ask_async("hello", replies.append)
    assert replies == ["async hi"]
    assert started, "the request must run off the calling thread in real use"


@pytest.mark.parametrize("persona_fragment", ["desktop pet", "two short sentences"])
def test_persona_keeps_replies_pet_sized(persona_fragment: str) -> None:
    assert persona_fragment in DEFAULT_PERSONA
