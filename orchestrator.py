from agents.environment_agent import EnvironmentAgent
from agents.weather_agent import WeatherAgent
from agents.notification_agent import NotificationAgent
from agents.care_agent import CareAgent
from agents.watering_predictor import WateringPredictor
from services.dynamodb_service import DynamoDBService

from models.sensor_data import SensorData


class GreenPulseOrchestrator:

    def __init__(self):
        self.environment_agent = EnvironmentAgent()
        self.weather_agent = WeatherAgent()
        self.notification_agent = NotificationAgent()
        self.care_agent = CareAgent()

        # Watering prediction
        self.watering_predictor = WateringPredictor()
        self.dynamodb_service = DynamoDBService()

    def process(
        self,
        sensor_data,
        environment_result=None,
        weather_result=None,
    ):
        # =============================================
        # 1. ENVIRONMENT AGENT
        # =============================================

        if environment_result is None:
            environment_result = self.environment_agent.process(
                sensor_data
            )

        print("\n========== ENVIRONMENT AGENT ==========")
        print(environment_result)

                # =============================================
        # 2. WATERING PREDICTOR
        # =============================================

        prediction_result = {
            "model_status": "unavailable",
            "reason": "Prediction has not been executed."
        }

        try:
            historical_readings = (
                self.dynamodb_service.get_recent_sensor_readings(
                    device_id=sensor_data.device_id,
                    limit=1000
                )
            )

            prediction_result = self.watering_predictor.predict(
                historical_readings
            )

        except Exception as e:
            print("Watering prediction failed:")
            print(e)

            prediction_result = {
                "model_status": "unavailable",
                "reason": "An error occurred while generating the prediction."
            }

        print("\n========== WATERING PREDICTOR ==========")
        print(prediction_result)

        # =============================================
        # 2. WEATHER AGENT
        # =============================================

        if weather_result is None:
            weather_result = self.weather_agent.process()

        print("\n========== WEATHER AGENT ==========")
        print(weather_result)

        # =============================================
        # 3. FETCH RECENT CARE EMAILS
        # =============================================

        email_result = self.notification_agent.fetch_care_emails()

        print("\n========== CARE EMAIL FETCH ==========")
        print(f"Status: {email_result.get('status')}")
        print(f"Emails found: {email_result.get('count', 0)}")

        # Maintain compatibility with the existing CareAgent,
        # which expects messages_found and relevant_messages.

        notification_context = {
            "messages_found": email_result.get("count", 0),
            "relevant_messages": email_result.get("emails", []),
            "status": email_result.get("status", "failed"),
        }

        # =============================================
        # 4. CARE AGENT
        # =============================================

        care_result = self.care_agent.process(
            environment_result,
            weather_result,
            notification_context,
            sensor_data,
        )

        print("\n========== CARE AGENT ==========")
        print(care_result)

        # =============================================
        # 5. SEND CARE SUMMARY EMAIL
        # =============================================

        email_delivery_result = (
            self.notification_agent.send_care_email(
                care_result=care_result,
                sensor_data=sensor_data,
                weather_data=weather_result,
            )
        )

        print("\n========== EMAIL DELIVERY ==========")
        print(email_delivery_result)

        # =============================================
        # 6. RETURN COMPLETE PIPELINE RESULTS
        # =============================================

        return {
            "sensor_data": sensor_data,
            "environment": environment_result,
            "weather": weather_result,
            "notifications": notification_context,
            "care": care_result,
            "email_delivery": email_delivery_result,
            "care_emails": email_result,
            "prediction": prediction_result,
        }