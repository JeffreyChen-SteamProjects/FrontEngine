"""
天氣資料來源：使用 Open-Meteo 的免金鑰 API，只送出座標、不帶任何身分資訊；
以標準函式庫發出請求（無新相依），並在背景執行緒抓取後快取，避免卡住 UI。

Weather via Open-Meteo's key-free API: only coordinates are sent, no identity.
Requests use the standard library (no new dependency) and run on a background
thread with a cached result so the UI never blocks.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.parse
import urllib.request
from typing import Dict, Optional, Tuple

from frontengine.utils.logging.loggin_instance import front_engine_logger

_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
_REQUEST_TIMEOUT = 10
_CACHE_SECONDS = 600

# WMO 天氣代碼 -> 說明 / WMO weather codes -> description
_WEATHER_CODES: Dict[int, str] = {
    0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Rime fog", 51: "Light drizzle", 53: "Drizzle",
    55: "Heavy drizzle", 56: "Freezing drizzle", 57: "Freezing drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain", 66: "Freezing rain",
    67: "Freezing rain", 71: "Light snow", 73: "Snow", 75: "Heavy snow",
    77: "Snow grains", 80: "Light showers", 81: "Showers", 82: "Violent showers",
    85: "Snow showers", 86: "Heavy snow showers", 95: "Thunderstorm",
    96: "Thunderstorm with hail", 99: "Thunderstorm with hail",
}


def describe_weather_code(code) -> str:
    """把 WMO 天氣代碼轉成說明文字；未知代碼回傳 "Unknown"。"""
    try:
        return _WEATHER_CODES.get(int(code), "Unknown")
    except (TypeError, ValueError):
        return "Unknown"


def build_forecast_url(latitude: float, longitude: float, unit: str = "celsius") -> str:
    """組出 Open-Meteo 的查詢網址（只帶座標與單位）。"""
    query = urllib.parse.urlencode({
        "latitude": f"{float(latitude):.4f}",
        "longitude": f"{float(longitude):.4f}",
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
        "temperature_unit": "fahrenheit" if str(unit).lower().startswith("f") else "celsius",
    })
    return f"{_FORECAST_URL}?{query}"


def build_geocode_url(city: str) -> str:
    """組出地名查座標的網址。"""
    query = urllib.parse.urlencode({"name": str(city), "count": 1, "format": "json"})
    return f"{_GEOCODE_URL}?{query}"


def parse_forecast(payload) -> Dict[str, object]:
    """把 Open-Meteo 的回應轉成樣板欄位；缺欄位以 None 表示。"""
    current = (payload or {}).get("current") or {}
    units = (payload or {}).get("current_units") or {}
    code = current.get("weather_code")
    return {
        "temperature": current.get("temperature_2m"),
        "unit": units.get("temperature_2m", "°C"),
        "humidity": current.get("relative_humidity_2m"),
        "wind": current.get("wind_speed_10m"),
        "code": code,
        "description": describe_weather_code(code) if code is not None else None,
    }


def parse_geocode(payload) -> Optional[Tuple[float, float, str]]:
    """從地名查詢結果取出 (緯度, 經度, 顯示名稱)；查不到回傳 None。"""
    results = (payload or {}).get("results") or []
    if not results:
        return None
    first = results[0]
    try:
        return (float(first["latitude"]), float(first["longitude"]), str(first.get("name", "")))
    except (KeyError, TypeError, ValueError):
        return None


def fetch_json(url: str, opener=urllib.request.urlopen):
    """抓取並解析 JSON；任何網路或格式錯誤都回傳 None。"""
    try:
        with opener(url, timeout=_REQUEST_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as error:  # pragma: no cover - network boundary
        front_engine_logger.warning(f"[weather] request failed: {error!r}")
        return None


def lookup_city(city: str, opener=urllib.request.urlopen) -> Optional[Tuple[float, float, str]]:
    """以地名查座標 / Resolve a city name to coordinates."""
    if not str(city or "").strip():
        return None
    return parse_geocode(fetch_json(build_geocode_url(city), opener=opener))


class WeatherService:
    """
    快取式天氣來源：current() 立即回傳最後一次的結果，過期時才在背景執行緒更新，
    因此呼叫端（繪圖迴圈）永遠不會被網路請求卡住。
    """

    def __init__(self, latitude: float = 25.033, longitude: float = 121.5654,
                 unit: str = "celsius", cache_seconds: int = _CACHE_SECONDS,
                 opener=urllib.request.urlopen) -> None:
        self.latitude = float(latitude)
        self.longitude = float(longitude)
        self.unit = unit
        self.cache_seconds = max(60, int(cache_seconds))
        self._opener = opener
        self._values: Dict[str, object] = {}
        self._fetched_at = 0.0
        self._lock = threading.Lock()
        self._refreshing = False

    def set_location(self, latitude: float, longitude: float) -> None:
        """換地點後清掉快取，下次讀取即重新抓取。"""
        with self._lock:
            self.latitude = float(latitude)
            self.longitude = float(longitude)
            self._values = {}
            self._fetched_at = 0.0

    def current(self) -> Dict[str, object]:
        """回傳目前的天氣欄位；過期時順便觸發一次背景更新。"""
        with self._lock:
            expired = (time.monotonic() - self._fetched_at) > self.cache_seconds
            values = dict(self._values)
        if expired:
            self.refresh_async()
        return values

    def refresh_async(self) -> None:
        """在背景執行緒更新一次（同時間只會有一個更新在跑）。"""
        with self._lock:
            if self._refreshing:
                return
            self._refreshing = True
        thread = threading.Thread(target=self._refresh, name="frontengine-weather", daemon=True)
        thread.start()

    def refresh(self) -> Dict[str, object]:
        """同步更新一次（測試用；正式路徑走 refresh_async）。"""
        self._refresh()
        with self._lock:
            return dict(self._values)

    def _refresh(self) -> None:
        with self._lock:
            latitude, longitude, unit = self.latitude, self.longitude, self.unit
        payload = fetch_json(build_forecast_url(latitude, longitude, unit), opener=self._opener)
        values = parse_forecast(payload) if payload else {}
        with self._lock:
            self._refreshing = False
            if values.get("temperature") is None:
                return
            self._values = values
            self._fetched_at = time.monotonic()


_weather_singleton: Optional[WeatherService] = None


def weather_service() -> WeatherService:
    """共用的天氣來源單例。"""
    global _weather_singleton
    if _weather_singleton is None:
        _weather_singleton = WeatherService()
    return _weather_singleton


def current_weather() -> Dict[str, object]:
    """便利函式：取得目前天氣欄位（第一次呼叫會先觸發背景抓取，暫時回傳空值）。"""
    return weather_service().current()
