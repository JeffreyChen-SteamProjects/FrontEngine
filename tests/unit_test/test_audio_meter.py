"""
音訊電表相關的純邏輯測試：包絡平滑、螢幕與輸出端點的比對，以及在沒有可用
音訊裝置時的退化行為（不需要真實硬體）。

Tests for the audio meter helpers: envelope smoothing, screen-to-endpoint
matching, and graceful degradation when no audio device is available — none of
which needs real hardware.
"""
from frontengine.utils.audio_meter.audio_envelope import AudioEnvelope, clamp_level
from frontengine.utils.audio_meter.screen_audio import (
    ScreenAudioMeters, audio_level_provider_for_screen, match_device_for_screen, name_tokens,
    screen_hints,
)
from frontengine.utils.audio_meter.system_audio_meter import list_output_devices, system_audio_level

DEVICES = [
    ("{id-default}", "Speakers (Realtek(R) Audio)"),
    ("{id-lg}", "LG HDR 4K (NVIDIA High Definition Audio)"),
    ("{id-dell}", "DELL U2718Q (Intel(R) Display Audio)"),
]


class FakeScreen:
    """假的 QScreen，只提供比對用的三個欄位 / A stand-in exposing the matched fields."""

    def __init__(self, model: str = "", manufacturer: str = "", name: str = "") -> None:
        self._model = model
        self._manufacturer = manufacturer
        self._name = name

    def model(self) -> str:
        return self._model

    def manufacturer(self) -> str:
        return self._manufacturer

    def name(self) -> str:
        return self._name


# --- clamp_level ----------------------------------------------------------
def test_clamp_level_bounds_and_junk() -> None:
    assert clamp_level(0.5) == 0.5
    assert clamp_level(9.0) == 1.0
    assert clamp_level(-3.0) == 0.0
    assert clamp_level("loud") == 0.0
    assert clamp_level(None) == 0.0


# --- AudioEnvelope --------------------------------------------------------
def test_envelope_starts_silent() -> None:
    envelope = AudioEnvelope()
    assert envelope.value == 0.0
    assert envelope.rms() == 0.0


def test_envelope_silence_stays_silent() -> None:
    envelope = AudioEnvelope()
    for _ in range(10):
        envelope.push(0.0)
    assert envelope.value == 0.0


def test_envelope_rises_monotonically_to_the_input() -> None:
    envelope = AudioEnvelope()
    values = [envelope.push(1.0) for _ in range(30)]
    assert all(later >= earlier for earlier, later in zip(values, values[1:]))
    assert all(0.0 <= value <= 1.0 for value in values)
    assert values[0] < 0.9, "attack should not be instant"
    assert values[-1] > 0.98, "sustained input should reach full scale"


def test_envelope_release_is_slower_than_attack() -> None:
    envelope = AudioEnvelope()
    rise = [envelope.push(1.0) for _ in range(30)]
    fall = [envelope.push(0.0) for _ in range(60)]
    rise_ticks = next(index for index, value in enumerate(rise) if value > 0.5)
    fall_ticks = next(index for index, value in enumerate(fall) if value < 0.5)
    assert fall_ticks > rise_ticks
    assert all(later <= earlier for earlier, later in zip(fall, fall[1:]))
    assert fall[-1] < 0.02


def test_envelope_smooths_alternating_peaks() -> None:
    envelope = AudioEnvelope()
    values = [envelope.push(1.0 if index % 2 == 0 else 0.0) for index in range(40)]
    tail = values[-10:]
    assert max(tail) - min(tail) < 0.25, "jitter should be smoothed out"
    assert 0.3 < sum(tail) / len(tail) < 0.95


def test_envelope_reset_clears_window_and_value() -> None:
    envelope = AudioEnvelope()
    for _ in range(10):
        envelope.push(1.0)
    envelope.reset()
    assert envelope.value == 0.0
    assert envelope.rms() == 0.0


def test_envelope_coefficients_are_clamped() -> None:
    envelope = AudioEnvelope(window=1, attack=2.0, decay=-1.0)
    assert envelope.attack == 1.0
    assert envelope.decay == 0.0
    assert envelope.push(1.0) == 1.0      # instant attack
    assert envelope.push(0.0) == 1.0      # no decay at all
    assert AudioEnvelope(window=0)._window == 1


def test_envelope_ignores_unusable_samples() -> None:
    envelope = AudioEnvelope()
    for _ in range(10):
        envelope.push("not a level")
    assert envelope.value == 0.0


# --- name_tokens / match_device_for_screen --------------------------------
def test_name_tokens_keeps_only_distinctive_words() -> None:
    assert name_tokens("LG HDR 4K") == {"lg", "hdr", "4k"}
    assert name_tokens("Digital Display Audio (NVIDIA High Definition Audio)") == set()
    assert name_tokens("Speakers(Realtek(R) Audio)") == set()
    assert name_tokens("") == set()
    assert name_tokens(None) == set()
    assert "u2718q" in name_tokens("DELL U2718Q (Intel(R) Display Audio)")


def test_match_device_prefers_the_best_scoring_endpoint() -> None:
    assert match_device_for_screen(["LG HDR 4K", "GSM"], DEVICES) == "{id-lg}"
    assert match_device_for_screen(["DELL U2718Q", "DEL"], DEVICES) == "{id-dell}"
    assert match_device_for_screen(["DELL U2718Q 4K"], DEVICES) == "{id-dell}"


def test_match_device_returns_none_without_a_shared_word() -> None:
    assert match_device_for_screen(["Generic PnP Monitor"], DEVICES) is None
    assert match_device_for_screen([r"\\.\DISPLAY1"], DEVICES) is None
    assert match_device_for_screen([], DEVICES) is None
    assert match_device_for_screen(["LG HDR 4K"], []) is None
    assert match_device_for_screen(None, None) is None


# --- screen_hints ---------------------------------------------------------
def test_screen_hints_orders_model_first_and_skips_blanks() -> None:
    assert screen_hints(FakeScreen("LG HDR 4K", "GSM", "DISPLAY2")) == ["LG HDR 4K", "GSM", "DISPLAY2"]
    assert screen_hints(FakeScreen("", "", "only-name")) == ["only-name"]
    assert screen_hints(object()) == []


def test_screen_hints_survives_a_raising_attribute() -> None:
    class BrokenScreen:
        def model(self):
            raise RuntimeError("no EDID")

        def name(self):
            return "ok"

    assert screen_hints(BrokenScreen()) == ["ok"]


# --- ScreenAudioMeters ----------------------------------------------------
def test_no_screen_falls_back_to_the_default_meter() -> None:
    meters = ScreenAudioMeters()
    assert meters.device_for_screen(None) is None
    assert meters.provider_for_screen(None) is system_audio_level
    assert audio_level_provider_for_screen(None) is system_audio_level


def test_unknown_device_degrades_instead_of_raising() -> None:
    meters = ScreenAudioMeters()
    assert meters.level_for_device("{no-such-device}") is None
    meters.close()
    assert meters._meters == {}
    meters.close()  # idempotent


def test_enumeration_shape_and_default_level() -> None:
    devices = list_output_devices()
    assert isinstance(devices, list)
    assert all(isinstance(device, tuple) and len(device) == 2 for device in devices)
    assert all(isinstance(device[0], str) and device[0] for device in devices)
    level = system_audio_level()
    assert level is None or 0.0 <= level <= 1.0
