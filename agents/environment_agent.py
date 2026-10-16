from typing import Dict, Any

from models.sensor_data import SensorData


class EnvironmentAgent:

    @staticmethod
    def process(sensor_data: SensorData) -> Dict[str, Any]:

        sm = sensor_data.soil_moisture

        if sm > 60:
            urgency = "LOW"

        elif 40 <= sm <= 60:
            urgency = "MEDIUM"

        elif 25 <= sm < 40:
            urgency = "HIGH"

        else:
            urgency = "CRITICAL"

        return {
            "soil_urgency": urgency,
            "environment_status": (
                f"Temp: {sensor_data.temperature}C, "
                f"Hum: {sensor_data.humidity}%"
            ),
            "reason": f"Soil moisture is at {sm}%"
        }