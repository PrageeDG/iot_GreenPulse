from services.dynamodb_service import DynamoDBService
from agents.watering_predictor import WateringPredictor


def main():
    db = DynamoDBService()

    readings = db.get_recent_sensor_readings(
        device_id="greenpulse-01",
        limit=1000,
    )

    predictor = WateringPredictor(
        watering_threshold=25.0,
        minimum_readings=20,
        minimum_history_hours=2.0,
        minimum_intervals=12,
    )

    result = predictor.predict(readings)

    print("\n========== REAL GREENPULSE PREDICTION ==========")

    for key, value in result.items():
        print(f"{key}: {value}")

    print("================================================")


if __name__ == "__main__":
    main()