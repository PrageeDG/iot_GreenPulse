import os
import time
from typing import Dict, Any

import requests


class WeatherAgent:
    def __init__(self):
        try:
            self.cache_ttl_seconds = float(
                os.getenv("WEATHER_CACHE_SECONDS", "300")
            )
        except ValueError:
            self.cache_ttl_seconds = 300.0

        self._cached_weather = None
        self._cached_at = 0.0
        self._cache_key = None

    def process(self) -> Dict[str, Any]:
        city = os.getenv("CITY_NAME", "Colombo")
        api_key = os.getenv("OPENWEATHER_API_KEY")
        cache_key = (
            city,
            bool(
                api_key
                and api_key != "YOUR_OPENWEATHER_API_KEY"
            ),
        )

        if (
            self._cached_weather is not None
            and self._cache_key == cache_key
            and time.monotonic() - self._cached_at
            < self.cache_ttl_seconds
        ):
            return dict(self._cached_weather)

        if not api_key or api_key == "YOUR_OPENWEATHER_API_KEY":
            weather = {
                "description": "mock weather",
                "temperature": 30.0,
                "rain_expected": False,
                "watering_hint": "Water normally"
            }
            self._cache_weather(weather, cache_key)
            return dict(weather)

        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={api_key}&units=metric"
        )

        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()

            data = response.json()
            desc = data["weather"][0]["description"]

            weather = {
                "description": desc,
                "temperature": data["main"]["temp"],
                "rain_expected": "rain" in desc.lower(),
                "watering_hint": (
                    "Hold watering if rain expected"
                    if "rain" in desc.lower()
                    else "Water normally"
                )
            }
            self._cache_weather(weather, cache_key)
            return dict(weather)

        except Exception:
            return {
                "description": "error fetching weather",
                "temperature": None,
                "rain_expected": False,
                "watering_hint": "Unknown"
            }

    def _cache_weather(self, weather, cache_key):
        self._cached_weather = weather
        self._cached_at = time.monotonic()
        self._cache_key = cache_key