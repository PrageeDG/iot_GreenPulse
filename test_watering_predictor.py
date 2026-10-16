from datetime import datetime, timedelta, timezone

from agents.watering_predictor import WateringPredictor


def generate_readings(
    values,
    interval_minutes=5,
    start_time=None,
):
    """Generate synthetic sensor readings."""

    if start_time is None:
        start_time = datetime(
            2026, 10, 13, 6, 0, tzinfo=timezone.utc
        )

    readings = []

    for index, moisture in enumerate(values):
        timestamp = start_time + timedelta(
            minutes=index * interval_minutes
        )

        readings.append({
            "device_id": "greenpulse-01",
            "timestamp": timestamp.isoformat(),
            "soil_moisture": moisture,
        })

    return readings


def run_test(name, test_function):
    try:
        test_function()
        print(f"PASS: {name}")
    except AssertionError as error:
        print(f"FAIL: {name} — {error}")
    except Exception as error:
        print(f"ERROR: {name} — {error}")


def test_drying_trend():
    # Gradual decline from 65% to 50%.
    readings = generate_readings([
        65, 64, 64, 63, 63,
        62, 62, 61, 61, 60,
        60, 59, 59, 58, 58,
        57, 57, 56, 56, 55,
        55, 54, 54, 53, 53,
        52, 52, 51, 51, 50,
    ])

    predictor = WateringPredictor(
        minimum_history_hours=2.0,
        minimum_intervals=12,
    )

    result = predictor.predict(readings)

    assert result["model_status"] == "available", result
    assert result["estimated_drying_rate_per_hour"] > 0
    assert result["predicted_hours_until_watering"] > 0
    assert result["predicted_at"]

    print("  Prediction:", result)


def test_stable_moisture():
    readings = generate_readings([60] * 40)

    predictor = WateringPredictor()

    result = predictor.predict(readings)

    assert result["model_status"] == "unavailable", result


def test_increasing_moisture():
    readings = generate_readings([
        50 + index * 0.5
        for index in range(40)
    ])

    predictor = WateringPredictor()

    result = predictor.predict(readings)

    assert result["model_status"] == "unavailable", result


def test_insufficient_history():
    readings = generate_readings([60, 59, 58, 57])

    predictor = WateringPredictor()

    result = predictor.predict(readings)

    assert result["model_status"] == "unavailable", result


def test_threshold_already_reached():
    readings = generate_readings([24] * 40)

    predictor = WateringPredictor()

    result = predictor.predict(readings)

    assert result["model_status"] == "threshold_reached", result
    assert result["predicted_hours_until_watering"] == 0


def test_isolated_low_reading():
    values = [
        62, 62, 62, 61, 62,
        61, 61, 62, 61, 61,
        61, 61, 60, 61, 61,
        61, 61, 60, 61, 61,
        61, 61, 60, 61, 61,
        61, 61, 60, 61, 54,
    ]

    readings = generate_readings(values)

    predictor = WateringPredictor()

    result = predictor.predict(readings)

    # The final isolated low reading should not, by itself,
    # create an extreme drying rate in the aggregated data.
    assert (
        result["model_status"] == "available"
        or result["model_status"] == "unavailable"
    )

    if result["model_status"] == "available":
        assert result["estimated_drying_rate_per_hour"] < 5


def test_prediction_timestamp_reference():
    values = [
        65 - index * 0.5
        for index in range(30)
    ]

    readings = generate_readings(values)

    predictor = WateringPredictor()

    result = predictor.predict(readings)

    if result["model_status"] == "available":
        predicted_at = datetime.fromisoformat(
            result["predicted_at"]
        )

        assert predicted_at.tzinfo is not None

        assert predicted_at > datetime.fromisoformat(
            readings[-1]["timestamp"]
        )


if __name__ == "__main__":
    print("\n========== WATERING PREDICTOR TESTS ==========\n")

    tests = [
        ("Drying trend", test_drying_trend),
        ("Stable moisture", test_stable_moisture),
        ("Increasing moisture", test_increasing_moisture),
        ("Insufficient history", test_insufficient_history),
        ("Threshold already reached", test_threshold_already_reached),
        ("Isolated low reading", test_isolated_low_reading),
        ("Prediction timestamp", test_prediction_timestamp_reference),
    ]

    for name, test in tests:
        run_test(name, test)

    print("\n===============================================\n")