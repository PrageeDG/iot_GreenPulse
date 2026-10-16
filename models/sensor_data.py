from dataclasses import dataclass


@dataclass
class SensorData:
    device_id: str
    timestamp: str
    temperature: float
    humidity: float
    soil_moisture: float
    light: float