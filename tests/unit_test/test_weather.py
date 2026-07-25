"""
天氣來源的測試：網址組裝、回應解析與快取行為都用假的 opener，不連網路。
Weather tests: URL building, response parsing and caching all run against a
fake opener, so no network call is made.
"""
import json
from io import BytesIO

from frontengine.utils.weather.weather_service import (
    WeatherService, build_forecast_url, build_geocode_url, describe_weather_code, fetch_json,
    lookup_city, parse_forecast, parse_geocode,
)

FORECAST = {
    "current": {"temperature_2m": 30.0, "relative_humidity_2m": 71,
                "wind_speed_10m": 13.1, "weather_code": 2},
    "current_units": {"temperature_2m": "°C"},
}
GEOCODE = {"results": [{"latitude": 25.05, "longitude": 121.53, "name": "Taipei"}]}


def fake_opener(payload, calls=None):
    """回傳一個假的 urlopen，記錄呼叫過的網址 / A urlopen stand-in recording URLs."""
    class _Response:
        def __init__(self, body):
            self._body = body

        def read(self):
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def opener(url, timeout=None):
        if calls is not None:
            calls.append(url)
        return _Response(json.dumps(payload).encode("utf-8"))

    return opener


# --- weather codes --------------------------------------------------------
def test_describe_weather_code() -> None:
    assert describe_weather_code(0) == "Clear"
    assert describe_weather_code(95) == "Thunderstorm"
    assert describe_weather_code(1234) == "Unknown"
    assert describe_weather_code(None) == "Unknown"
    assert describe_weather_code("3") == "Overcast", "numeric strings are accepted"


# --- URLs -----------------------------------------------------------------
def test_forecast_url_carries_only_coordinates_and_unit() -> None:
    url = build_forecast_url(25.033, 121.5654)
    assert url.startswith("https://api.open-meteo.com/v1/forecast?")
    assert "latitude=25.0330" in url and "longitude=121.5654" in url
    assert "temperature_unit=celsius" in url
    assert "fahrenheit" in build_forecast_url(1, 2, unit="fahrenheit")


def test_geocode_url_escapes_the_city() -> None:
    assert "name=New+York" in build_geocode_url("New York")


# --- parsing --------------------------------------------------------------
def test_parse_forecast_maps_every_field() -> None:
    values = parse_forecast(FORECAST)
    assert values["temperature"] == 30.0
    assert values["unit"] == "°C"
    assert values["humidity"] == 71
    assert values["wind"] == 13.1
    assert values["description"] == "Partly cloudy"


def test_parse_forecast_tolerates_missing_data() -> None:
    values = parse_forecast({})
    assert values["temperature"] is None and values["description"] is None
    assert parse_forecast(None)["temperature"] is None


def test_parse_geocode() -> None:
    assert parse_geocode(GEOCODE) == (25.05, 121.53, "Taipei")
    assert parse_geocode({"results": []}) is None
    assert parse_geocode(None) is None
    assert parse_geocode({"results": [{"latitude": "x"}]}) is None


# --- fetching -------------------------------------------------------------
def test_fetch_json_returns_none_on_failure() -> None:
    def broken(_url, timeout=None):
        raise OSError("offline")

    assert fetch_json("https://example.invalid", opener=broken) is None


def test_lookup_city_uses_the_geocoder() -> None:
    calls = []
    assert lookup_city("Taipei", opener=fake_opener(GEOCODE, calls)) == (25.05, 121.53, "Taipei")
    assert calls and "geocoding-api" in calls[0]
    assert lookup_city("", opener=fake_opener(GEOCODE)) is None


# --- service --------------------------------------------------------------
def test_service_caches_between_calls() -> None:
    calls = []
    service = WeatherService(1.0, 2.0, opener=fake_opener(FORECAST, calls))
    assert service.refresh()["temperature"] == 30.0
    assert len(calls) == 1
    assert service.current()["temperature"] == 30.0
    assert len(calls) == 1, "a fresh cache must not hit the network again"


def test_service_starts_empty_without_blocking() -> None:
    service = WeatherService(1.0, 2.0, opener=fake_opener(FORECAST))
    assert service.current() == {}, "the first read returns immediately, refreshing in the background"


def test_changing_location_clears_the_cache() -> None:
    service = WeatherService(1.0, 2.0, opener=fake_opener(FORECAST))
    service.refresh()
    service.set_location(50.0, 60.0)
    assert service._values == {}
    assert service.latitude == 50.0 and service.longitude == 60.0


def test_a_failed_refresh_keeps_the_previous_values() -> None:
    service = WeatherService(1.0, 2.0, opener=fake_opener(FORECAST))
    service.refresh()

    def broken(_url, timeout=None):
        raise OSError("offline")

    service._opener = broken
    assert service.refresh()["temperature"] == 30.0, "a failed update must not blank the overlay"
