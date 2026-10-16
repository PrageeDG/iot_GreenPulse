from datetime import datetime

from services.dynamodb_service import DynamoDBService


def parse_timestamp(value):
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


def main():
    db = DynamoDBService()

    readings = db.get_recent_sensor_readings(
        device_id="greenpulse-01",
        limit=1000
    )

    valid = []

    for reading in readings:
        try:
            timestamp = parse_timestamp(
                reading["timestamp"]
            )

            moisture = float(
                reading["soil_moisture"]
            )

            valid.append({
                "timestamp": timestamp,
                "soil_moisture": moisture
            })

        except (KeyError, TypeError, ValueError):
            continue

    valid.sort(key=lambda item: item["timestamp"])

    if len(valid) < 2:
        print("Insufficient readings.")
        return

    # Identify the latest large upward change.
    latest_reset_index = 0

    for i in range(1, len(valid)):
        change = (
            valid[i]["soil_moisture"]
            - valid[i - 1]["soil_moisture"]
        )

        if change >= 5:
            latest_reset_index = i

    # Analyse the readings after the latest large increase.
    recent = valid[latest_reset_index:]

    print("\n========== LATEST DRYING PERIOD ==========")
    print("Readings:", len(recent))

    print(
        "Start:",
        recent[0]["timestamp"].isoformat()
    )

    print(
        "End:",
        recent[-1]["timestamp"].isoformat()
    )

    print(
        "Starting moisture:",
        recent[0]["soil_moisture"]
    )

    print(
        "Latest moisture:",
        recent[-1]["soil_moisture"]
    )

    print("\n========== RECENT READINGS ==========")

    for item in recent[-30:]:
        print(
            f"{item['timestamp'].isoformat()} | "
            f"{item['soil_moisture']:.1f}%"
        )


if __name__ == "__main__":
    main()