from services.dynamodb_service import DynamoDBService


def main():
    db = DynamoDBService()

    readings = db.get_recent_sensor_readings(
        device_id="greenpulse-01",
        limit=10
    )

    print("\n========== RECENT SENSOR READINGS ==========")

    if not readings:
        print("No historical readings found.")
        return

    for reading in readings:
        print(
            f"Timestamp: {reading['timestamp']} | "
            f"Soil moisture: {reading['soil_moisture']} | "
            f"Temperature: {reading['temperature']} | "
            f"Humidity: {reading['humidity']} | "
            f"Light: {reading['light']}"
        )

    print("\nTotal readings retrieved:", len(readings))


if __name__ == "__main__":
    main()