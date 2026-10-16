from datetime import datetime, timezone

from services.dynamodb_service import DynamoDBService

DEVICE_ID = "greenpulse-01"

def main():
    db = DynamoDBService()

    readings = db.get_recent_sensor_readings(
        device_id=DEVICE_ID,
        limit=1000,
    )

    if not readings:
        print("No sensor readings found.")
        return

    # Sort chronologically.
    readings.sort(key=lambda r: r["timestamp"])

    # Display the latest 20 readings.
    latest = readings[-20:]

    print("\n========== PREDICTOR DATA INSPECTION ==========")
    print(f"Total readings retrieved: {len(readings)}")
    print(f"First timestamp: {readings[0]['timestamp']}")
    print(f"Latest timestamp: {readings[-1]['timestamp']}")

    first_time = datetime.fromisoformat(
        readings[0]["timestamp"].replace("Z", "+00:00")
    )
    last_time = datetime.fromisoformat(
        readings[-1]["timestamp"].replace("Z", "+00:00")
    )

    duration_hours = (
        last_time - first_time
    ).total_seconds() / 3600

    print(f"History duration: {duration_hours:.2f} hours")

    moisture_values = [
        float(r["soil_moisture"])
        for r in readings
    ]

    print(f"Minimum soil moisture: {min(moisture_values):.2f}%")
    print(f"Maximum soil moisture: {max(moisture_values):.2f}%")
    print(f"Latest soil moisture: {moisture_values[-1]:.2f}%")

    print("\nLatest 20 readings:")
    print("-" * 85)

    for reading in latest:
        print(
            f"{reading['timestamp']} | "
            f"Soil: {float(reading['soil_moisture']):6.2f}% | "
            f"Temp: {float(reading['temperature']):5.2f}°C | "
            f"Humidity: {float(reading['humidity']):5.2f}%"
        )

    print("-" * 85)

if __name__ == "__main__":
    main()