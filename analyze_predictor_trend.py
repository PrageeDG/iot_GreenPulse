from datetime import datetime

from services.dynamodb_service import DynamoDBService


DEVICE_ID = "greenpulse-01"


def parse_timestamp(value):
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


def main():
    db = DynamoDBService()

    readings = db.get_recent_sensor_readings(
        device_id=DEVICE_ID,
        limit=1000,
    )

    if not readings:
        print("No readings found.")
        return

    readings.sort(key=lambda r: r["timestamp"])

    # Group readings into five-minute intervals.
    intervals = {}

    for reading in readings:
        timestamp = parse_timestamp(reading["timestamp"])
        interval_key = timestamp.replace(
            minute=(timestamp.minute // 5) * 5,
            second=0,
            microsecond=0,
        )

        moisture = float(reading["soil_moisture"])

        intervals.setdefault(interval_key, []).append(moisture)

    print("\n========== FIVE-MINUTE SOIL TREND ==========")

    for timestamp, values in sorted(intervals.items()):
        print(
            f"{timestamp.isoformat()} | "
            f"Readings: {len(values):3d} | "
            f"Mean: {sum(values) / len(values):5.2f}% | "
            f"Min: {min(values):5.2f}% | "
            f"Max: {max(values):5.2f}%"
        )

    print("============================================")


if __name__ == "__main__":
    main()