from statistics import mean, median

from services.dynamodb_service import DynamoDBService


def main():
    db = DynamoDBService()

    readings = db.get_recent_sensor_readings(
        device_id="greenpulse-01",
        limit=1000
    )

    if not readings:
        print("No historical readings available.")
        return

    # Convert and sort readings chronologically.
    valid_readings = []

    for reading in readings:
        try:
            moisture = float(reading["soil_moisture"])
            timestamp = reading["timestamp"]

            valid_readings.append({
                "timestamp": timestamp,
                "soil_moisture": moisture
            })

        except (KeyError, TypeError, ValueError):
            continue

    valid_readings.sort(
        key=lambda item: item["timestamp"]
    )

    if not valid_readings:
        print("No valid soil-moisture readings.")
        return

    moisture_values = [
        item["soil_moisture"]
        for item in valid_readings
    ]

    print("\n========== SOIL HISTORY ANALYSIS ==========")

    print("Valid readings:", len(valid_readings))
    print("Oldest reading:", valid_readings[0]["timestamp"])
    print("Newest reading:", valid_readings[-1]["timestamp"])
    print("Minimum moisture:", min(moisture_values))
    print("Maximum moisture:", max(moisture_values))
    print("Mean moisture:", round(mean(moisture_values), 2))
    print("Median moisture:", median(moisture_values))

    print("\n========== LAST 20 READINGS ==========")

    for reading in valid_readings[-20:]:
        print(
            f"{reading['timestamp']} | "
            f"Soil moisture: {reading['soil_moisture']}"
        )

    print("\n========== LARGEST MOISTURE CHANGES ==========")

    changes = []

    for previous, current in zip(
        valid_readings,
        valid_readings[1:]
    ):
        change = (
            current["soil_moisture"]
            - previous["soil_moisture"]
        )

        changes.append({
            "timestamp": current["timestamp"],
            "change": change,
            "previous": previous["soil_moisture"],
            "current": current["soil_moisture"]
        })

    changes.sort(
        key=lambda item: abs(item["change"]),
        reverse=True
    )

    for item in changes[:10]:
        print(
            f"{item['timestamp']} | "
            f"Change: {item['change']:+.2f} | "
            f"{item['previous']} -> {item['current']}"
        )


if __name__ == "__main__":
    main()