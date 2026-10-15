import json
import os
from typing import Dict, Any

from openai import OpenAI

from models.sensor_data import SensorData


class CareAgent:

    @staticmethod
    def process(
        env_data: Dict[str, Any],
        weather_data: Dict[str, Any],
        notif_data: Dict[str, Any],
        sensor_data: SensorData
    ) -> Dict[str, Any]:

        llm_mode = os.getenv("LLM_MODE", "mock").lower()

        # ==========================================
        # MOCK MODE
        # ==========================================

        if llm_mode == "mock":

            rec = "Water the plant."

            if weather_data.get("rain_expected"):
                rec = (
                    "Hold off on watering because rain is expected."
                )

            elif env_data.get("soil_urgency") == "LOW":
                rec = "No need to water right now."

            if notif_data.get("messages_found", 0) > 0:
                rec += (
                    " Also, I noticed a relevant notification "
                    "you should check."
                )

            watering_required = (
                env_data["soil_urgency"] in ["HIGH", "CRITICAL"]
                and not weather_data.get("rain_expected", False)
            )

            return {
                "urgency": env_data["soil_urgency"],
                "recommendation": rec,
                "watering_required": watering_required,
                "reason": (
                    f"Decision based on "
                    f"{env_data['soil_urgency']} soil urgency, "
                    f"rain_expected="
                    f"{weather_data.get('rain_expected', False)}, "
                    f"notifications="
                    f"{notif_data.get('messages_found', 0)}."
                ),
                "literary_quote": (
                    "A garden grows through patience and care."
                )
            }

        # ==========================================
        # OPENAI MODE
        # ==========================================

        api_key = os.getenv("OPENAI_API_KEY")
        model_name = os.getenv(
            "OPENAI_MODEL",
            "gpt-5.4-mini"
        )

        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured."
            )

        sensor_dict = {
            "device_id": sensor_data.device_id,
            "timestamp": sensor_data.timestamp,
            "temperature": sensor_data.temperature,
            "humidity": sensor_data.humidity,
            "soil_moisture": sensor_data.soil_moisture,
            "light": sensor_data.light
        }

        prompt = f"""
You are the GreenPulse plant-care decision agent.

The monitored plant is an indoor banyan plant
(Ficus microcarpa).

Analyze the current sensor data, environment assessment,
weather information, and relevant notifications.

Sensor Data:
{json.dumps(sensor_dict, indent=2)}

Environment:
{json.dumps(env_data, indent=2)}

Weather:
{json.dumps(weather_data, indent=2)}

Notifications:
{json.dumps(notif_data, indent=2)}

Provide practical plant-care advice.

Return ONLY valid JSON using exactly this structure:

{{
  "urgency": "LOW | MEDIUM | HIGH | CRITICAL",
  "recommendation": "Short actionable recommendation",
  "reason": "Explain why this recommendation was made",
  "watering_required": true | false,
  "literary_quote": "Short suitable gardening quote"
}}

The watering_required field must be true only when watering is
actually recommended based on the current soil condition and
weather information.

If rain is expected and watering should be postponed,
watering_required must be false.
Do not invent sensor readings.
Base your decision on the provided data.
"""

        try:

            client = OpenAI(
                api_key=api_key,
                max_retries=0,
                timeout=15.0
            )

            response = client.responses.create(
                model=model_name,
                input=prompt
            )

            raw_output = response.output_text.strip()

            result = json.loads(raw_output)

            return {
                "urgency": result.get(
                    "urgency",
                    env_data["soil_urgency"]
                ),
                "recommendation": result.get(
                    "recommendation",
                    "Monitor the plant conditions."
                ),
                "watering_required": result.get(
                    "watering_required",
                    False
                ),
                "reason": result.get(
                    "reason",
                    "Based on the available environmental data."
                ),
                "literary_quote": result.get(
                    "literary_quote",
                    "A garden grows through patience and care."
                )
            }

        except Exception as e:

            print("OpenAI Care Agent error:")
            print(e)

            # Safe fallback
            return {
                "urgency": env_data["soil_urgency"],
                "recommendation": (
                    "Unable to generate AI advice. "
                    "Please monitor the plant conditions."
                ),
                "watering_required": False,
                "reason": "OpenAI Care Agent unavailable.",
                "literary_quote": (
                    "A garden grows through patience and care."
                )
            }