from datetime import datetime, timezone, timedelta
from statistics import median, mean
import math


class WateringPredictor:

    def __init__(
        self,
        watering_threshold=25.0,
        minimum_readings=20,
        minimum_history_hours=2.0,
        minimum_intervals=12,
        interval_minutes=5,
        minimum_drying_rate=0.01,
        maximum_prediction_hours=72.0,
    ):
        self.watering_threshold = watering_threshold
        self.minimum_readings = minimum_readings
        self.minimum_history_hours = minimum_history_hours
        self.minimum_intervals = minimum_intervals
        self.interval_minutes = interval_minutes
        self.minimum_drying_rate = minimum_drying_rate
        self.maximum_prediction_hours = maximum_prediction_hours

    @staticmethod
    def parse_timestamp(timestamp):
        """Convert an ISO timestamp to a UTC-aware datetime."""

        try:
            parsed = datetime.fromisoformat(
                timestamp.replace("Z", "+00:00")
            )

            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)

            return parsed.astimezone(timezone.utc)

        except (ValueError, TypeError, AttributeError):
            return None

    def _aggregate_readings(self, readings):
        """Aggregate valid readings into fixed time intervals."""

        valid_readings = []

        for reading in readings:
            timestamp = self.parse_timestamp(
                reading.get("timestamp")
            )

            try:
                moisture = float(reading["soil_moisture"])
            except (KeyError, TypeError, ValueError):
                continue

            if timestamp is None:
                continue

            if not math.isfinite(moisture):
                continue

            if not 0 <= moisture <= 100:
                continue

            valid_readings.append({
                "timestamp": timestamp,
                "soil_moisture": moisture,
            })

        valid_readings.sort(
            key=lambda item: item["timestamp"]
        )

        if not valid_readings:
            return [], []

        # Group readings into fixed intervals measured from UTC epoch.
        buckets = {}

        for reading in valid_readings:
            timestamp = reading["timestamp"]

            epoch_seconds = timestamp.timestamp()
            interval_seconds = self.interval_minutes * 60

            bucket_epoch = (
                int(epoch_seconds // interval_seconds)
                * interval_seconds
            )

            bucket_time = datetime.fromtimestamp(
                bucket_epoch,
                tz=timezone.utc,
            )

            buckets.setdefault(bucket_time, []).append(
                reading["soil_moisture"]
            )

        aggregated = []

        for timestamp, values in sorted(buckets.items()):
            aggregated.append({
                "timestamp": timestamp,
                "soil_moisture": median(values),
                "sample_count": len(values),
            })

        return valid_readings, aggregated

    @staticmethod
    def _linear_regression(points):
        """
        Fit moisture = intercept + slope * elapsed_hours.

        Returns slope, intercept, and R-squared.
        """

        if len(points) < 2:
            return None

        start_time = points[0]["timestamp"]

        x_values = [
            (
                point["timestamp"] - start_time
            ).total_seconds() / 3600.0
            for point in points
        ]

        y_values = [
            point["soil_moisture"]
            for point in points
        ]

        x_mean = mean(x_values)
        y_mean = mean(y_values)

        denominator = sum(
            (x - x_mean) ** 2
            for x in x_values
        )

        if denominator <= 0:
            return None

        slope = sum(
            (x - x_mean) * (y - y_mean)
            for x, y in zip(x_values, y_values)
        ) / denominator

        intercept = y_mean - slope * x_mean

        predicted_values = [
            intercept + slope * x
            for x in x_values
        ]

        total_variation = sum(
            (y - y_mean) ** 2
            for y in y_values
        )

        residual_variation = sum(
            (y - predicted) ** 2
            for y, predicted in zip(
                y_values,
                predicted_values,
            )
        )

        if total_variation <= 0:
            r_squared = 1.0 if residual_variation == 0 else 0.0
        else:
            r_squared = max(
                0.0,
                min(
                    1.0,
                    1.0 - residual_variation / total_variation,
                ),
            )

        return slope, intercept, r_squared

    def predict(self, readings):

        if not readings:
            return {
                "model_status": "unavailable",
                "reason": "No historical readings available.",
            }

        valid_readings, aggregated = self._aggregate_readings(
            readings
        )

        if len(valid_readings) < self.minimum_readings:
            return {
                "model_status": "unavailable",
                "reason": "Insufficient valid historical readings.",
            }

        if not aggregated:
            return {
                "model_status": "unavailable",
                "reason": "No valid aggregated readings available.",
            }

        history_hours = (
            valid_readings[-1]["timestamp"]
            - valid_readings[0]["timestamp"]
        ).total_seconds() / 3600.0

        if history_hours < self.minimum_history_hours:
            return {
                "model_status": "unavailable",
                "reason": "Historical time span is too short.",
                "history_hours": round(history_hours, 2),
            }

        if len(aggregated) < self.minimum_intervals:
            return {
                "model_status": "unavailable",
                "reason": "Insufficient time intervals for prediction.",
                "history_hours": round(history_hours, 2),
                "intervals_used": len(aggregated),
            }

        current_moisture = valid_readings[-1]["soil_moisture"]

        # Use the latest aggregated interval to avoid letting
        # a single instantaneous reading dominate the prediction.
        latest_interval_moisture = aggregated[-1]["soil_moisture"]

        # If the threshold has been reached, do not extrapolate.
        if current_moisture <= self.watering_threshold:
            return {
                "model_status": "threshold_reached",
                "current_soil_moisture": round(
                    current_moisture, 2
                ),
                "watering_threshold": self.watering_threshold,
                "predicted_hours_until_watering": 0,
            }

        regression = self._linear_regression(aggregated)

        if regression is None:
            return {
                "model_status": "unavailable",
                "reason": "Insufficient variation in timestamps.",
            }

        slope, intercept, r_squared = regression

        if slope >= 0:
            return {
                "model_status": "unavailable",
                "reason": "Soil moisture is not showing a drying trend.",
                "current_soil_moisture": round(
                    current_moisture, 2
                ),
                "watering_threshold": self.watering_threshold,
                "history_hours": round(history_hours, 2),
                "drying_rate_per_hour": round(slope, 4),
            }

        drying_rate = abs(slope)

        if drying_rate < self.minimum_drying_rate:
            return {
                "model_status": "unavailable",
                "reason": "Drying rate is too small to estimate reliably.",
                "current_soil_moisture": round(
                    current_moisture, 2
                ),
                "watering_threshold": self.watering_threshold,
                "history_hours": round(history_hours, 2),
                "drying_rate_per_hour": round(drying_rate, 4),
            }

        # Low R-squared means a straight line does not explain
        # the observed trend well enough for extrapolation.
        if r_squared < 0.50:
            return {
                "model_status": "unavailable",
                "reason": (
                    "Soil-moisture trend is too inconsistent "
                    "for a reliable prediction."
                ),
                "current_soil_moisture": round(
                    current_moisture, 2
                ),
                "watering_threshold": self.watering_threshold,
                "history_hours": round(history_hours, 2),
                "r_squared": round(r_squared, 3),
            }

        # Use the same aggregated reading as the prediction reference.
        reference_timestamp = aggregated[-1]["timestamp"]
        reference_moisture = latest_interval_moisture

        hours_remaining = (
            reference_moisture - self.watering_threshold
        ) / drying_rate

        if hours_remaining <= 0:
            return {
                "model_status": "unavailable",
                "reason": "The fitted trend does not support a future estimate.",
            }

        if hours_remaining > self.maximum_prediction_hours:
            return {
                "model_status": "unavailable",
                "reason": (
                    "Estimated time exceeds the prediction horizon. "
                    "Collect more historical readings."
                ),
                "current_soil_moisture": round(
                    current_moisture, 2
                ),
                "watering_threshold": self.watering_threshold,
                "estimated_drying_rate_per_hour": round(
                    drying_rate, 4
                ),
                "history_hours": round(history_hours, 2),
                "r_squared": round(r_squared, 3),
            }

        prediction_quality = self._assess_prediction_quality(
            history_hours=history_hours,
            r_squared=r_squared,
            predicted_hours_until_watering=hours_remaining,
        )

        predicted_at = (
            reference_timestamp
            + timedelta(hours=hours_remaining)
        )

        return {
            "model_status": "available",
            "prediction_quality": prediction_quality,
            "current_soil_moisture": round(
                current_moisture, 2
            ),
            "latest_interval_moisture": round(
                latest_interval_moisture, 2
            ),
            "watering_threshold": self.watering_threshold,
            "estimated_drying_rate_per_hour": round(
                drying_rate, 4
            ),
            "predicted_hours_until_watering": round(
                hours_remaining, 2
            ),
            "predicted_at": predicted_at.isoformat(),
            "history_hours": round(history_hours, 2),
            "readings_used": len(valid_readings),
            "intervals_used": len(aggregated),
            "r_squared": round(r_squared, 3),
        }

    def _assess_prediction_quality(
        self,
        history_hours,
        r_squared,
        predicted_hours_until_watering
    ):
        """
        Assign a prototype quality label based on history length,
        trend fit, and how far into the future we are predicting.

        These labels are heuristic indicators, not calibrated
        statistical confidence levels.
        """

        # LOW: Limited history, weak trend, or long extrapolation
        if (
            history_hours < 12
            or r_squared < 0.60
            or predicted_hours_until_watering > history_hours * 4
        ):
            return "LOW"

        # MODERATE: More evidence is available, but uncertainty remains
        if (
            history_hours < 48
            or r_squared < 0.80
            or predicted_hours_until_watering > history_hours * 2
        ):
            return "MODERATE"

        # HIGH: Longer history and a consistent trend
        return "HIGH"