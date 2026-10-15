import os
from typing import Dict, Any

import requests


class WeatherAgent:
    @staticmethod
    def process() -> Dict[str, Any]:
        city = os.getenv("CITY_NAME", "Colombo")
        api_key = os.getenv("OPENWEATHER_API_KEY")

        if not api_key or api_key == "YOUR_OPENWEATHER_API_KEY":
            return {
                "description": "mock weather",
                "temperature": 30.0,
                "rain_expected": False,
                "watering_hint": "Water normally"
            }

        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={api_key}&units=metric"
        )

        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()

            data = response.json()
            desc = data["weather"][0]["description"]

            return {
                "description": desc,
                "temperature": data["main"]["temp"],
                "rain_expected": "rain" in desc.lower(),
                "watering_hint": (
                    "Hold watering if rain expected"
                    if "rain" in desc.lower()
                    else "Water normally"
                )
            }

        except Exception:
            return {
                "description": "error fetching weather",
                "temperature": None,
                "rain_expected": False,
                "watering_hint": "Unknown"
            }