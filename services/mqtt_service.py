import json
import ssl
import threading
import time

import paho.mqtt.client as mqtt

import config
from models.sensor_data import SensorData
from orchestrator import GreenPulseOrchestrator
from services.dynamodb_service import DynamoDBService
from validators.care_validator import (
    validate_care_response,
    CareValidationError,
)


class MQTTService:

    def __init__(self):

        self.client = mqtt.Client(
            client_id=config.CLIENT_ID
        )

        # =====================================================
        # TLS CONFIGURATION
        # =====================================================

        self.client.tls_set(
            ca_certs=config.ROOT_CA,
            certfile=config.CERTIFICATE,
            keyfile=config.PRIVATE_KEY,
            tls_version=ssl.PROTOCOL_TLSv1_2
        )

        # =====================================================
        # CALLBACKS
        # =====================================================

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        # =====================================================
        # DATABASE
        # =====================================================

        self.dynamodb = DynamoDBService()
        self.orchestrator = GreenPulseOrchestrator()

        # Care decision state
        self.last_care_state = None

    # =========================================================
    # CONNECT
    # =========================================================

    def connect(self):

        print()
        print("========================================")
        print("Connecting to AWS IoT Core...")
        print("========================================")

        self.client.connect(
            config.AWS_IOT_ENDPOINT,
            8883,
            keepalive=60
        )

        self.client.loop_start()

    # =========================================================
    # CONNECT CALLBACK
    # =========================================================

    def on_connect(self, client, userdata, flags, rc):

        if rc == 0:

            print("AWS IoT MQTT connected!")

            result = client.subscribe(
                config.SENSOR_TOPIC
            )

            if result[0] == mqtt.MQTT_ERR_SUCCESS:

                print(
                    f"Subscribed to: "
                    f"{config.SENSOR_TOPIC}"
                )

            else:

                print(
                    "Sensor topic subscription failed!"
                )

            # Status topic
            result = client.subscribe(
                config.STATUS_TOPIC
            )

            if result[0] == mqtt.MQTT_ERR_SUCCESS:

                print(
                    f"Subscribed to: "
                    f"{config.STATUS_TOPIC}"
                )

            else:

                print(
                    "Status topic subscription failed!"
                )

        else:

            print(
                f"MQTT connection failed. "
                f"Return code: {rc}"
            )

        

    # =========================================================
    # MESSAGE CALLBACK
    # =========================================================

    def on_message(self, client, userdata, msg):

        print()
        print("========================================")
        print("MQTT MESSAGE RECEIVED")
        print("========================================")

        print(f"Topic: {msg.topic}")

        try:

            payload = msg.payload.decode("utf-8")

            print(f"Payload: {payload}")

            data = json.loads(payload)

        except Exception as e:

            print("Failed to decode MQTT message:")
            print(e)

            return

        # =====================================================
        # SENSOR DATA
        # =====================================================

        if msg.topic == config.SENSOR_TOPIC:

            self.handle_sensor_data(data)

        # =====================================================
        # DEVICE STATUS
        # =====================================================

        elif msg.topic == config.STATUS_TOPIC:

            print(
                f"Device status: "
                f"{data.get('status')}"
            )

        print("========================================")

    # =========================================================
    # SENSOR DATA HANDLER
    # =========================================================

    def _get_care_state(self, sensor_data):
        """Return the inputs that determine whether care advice changed."""
        environment_result = self.orchestrator.environment_agent.process(
            sensor_data
        )
        weather_result = self.orchestrator.weather_agent.process()

        watering_required = (
            environment_result["soil_urgency"] in ["HIGH", "CRITICAL"]
            and not weather_result.get("rain_expected", False)
        )

        return (
            environment_result,
            weather_result,
            (
                environment_result["soil_urgency"],
                watering_required,
            ),
        )

    def handle_sensor_data(self, data):
        print(
        f"PROCESSING SENSOR READING: "
        f"{data.get('device_id')} | "
        f"{data.get('timestamp')}"
        )

        try:

            sensor_data = SensorData(
                device_id=data["device_id"],
                timestamp=data["timestamp"],
                temperature=float(
                    data["temperature"]
                ),
                humidity=float(
                    data["humidity"]
                ),
                soil_moisture=float(
                    data["soil_moisture"]
                ),
                light=float(
                    data["light"]
                )
            )

        except (KeyError, ValueError, TypeError) as e:

            print(
                "Invalid sensor payload:"
            )

            print(e)

            return

        # =====================================================
        # DISPLAY
        # =====================================================

        print()
        print("Device:", sensor_data.device_id)
        print(
            "Temperature:",
            sensor_data.temperature,
            "°C"
        )
        print(
            "Humidity:",
            sensor_data.humidity,
            "%"
        )
        print(
            "Soil moisture:",
            sensor_data.soil_moisture,
            "%"
        )
        print(
            "Light:",
            sensor_data.light,
            "lux"
        )
        print("Timestamp:", sensor_data.timestamp)

        # =====================================================
        # SAVE TO DYNAMODB
        # =====================================================

        try:

            self.dynamodb.save_sensor_reading(
                sensor_data
            )

        except Exception as e:

            print(
                "DynamoDB write failed:"
            )

            print(e)

        # =====================================================
        # AGENT PROCESSING
        # =====================================================

        try:
            environment_result, weather_result, care_state = (
                self._get_care_state(sensor_data)
            )
        except Exception as e:
            print("Care state evaluation failed:")
            print(e)
            return

        state_changed = care_state != self.last_care_state

        if (
            self.last_care_state is None
            or state_changed
        ):

            print()
            print("========== CARE DECISION TRIGGERED ==========")

            try:

                pipeline_result = self.orchestrator.process(
                    sensor_data,
                    environment_result=environment_result,
                    weather_result=weather_result,
                )

                print(
                    "========== PIPELINE COMPLETE =========="
                )

                care_result = pipeline_result.get("care")

                if care_result is None:

                    print(
                        "ERROR: Care result was not returned "
                        "by orchestrator."
                    )

                else:

                    print(
                        "Care result obtained from orchestrator:"
                    )
                    print(care_result)

                    # 1. Validate the Care Agent response.
                    try:

                        validated_care = validate_care_response(
                            response=care_result,
                            env_data=pipeline_result.get(
                                "environment", {}
                            ),
                            weather_data=pipeline_result.get(
                                "weather", {}
                            ),
                        )

                        print("Care response validation: PASSED")

                        # 2. Publish only the validated care result.
                        self.publish_care_result(validated_care)

                    except CareValidationError as validation_error:

                        print("Care response validation: FAILED")
                        print(f"Reason: {validation_error}")

                        # Do not publish the rejected care response.

                    # 3. Publish weather data independently.
                    self.publish_weather_result(
                        pipeline_result.get("weather", {})
                    )

                    # 4. Publish watering prediction.
                    self.publish_prediction_result(
                        pipeline_result.get("prediction", {})
                    )

                    # 5. Publish email status and recent care emails.
                    self.publish_notification_result(
                        pipeline_result
                    )

                    # 6. Remember the state that produced this decision.
                    self.last_care_state = care_state

                    print(
                        "======================================="
                    )

            except Exception as e:

                print(
                    "Agent pipeline processing failed:"
                )
                print(e)

        else:
            print(
                "Care decision skipped. "
                "Urgency and watering decision are unchanged."
            )
        
        # =====================================================
        # PUBLISH CARE RESULT
        # =====================================================

    def publish_care_result(self, care_result):
        try:
            payload = json.dumps(care_result)

            print("========== CARE MQTT PUBLISH ==========")
            print("Topic:", config.CARE_TOPIC)
            print("Payload:", payload)

            result = self.client.publish(
                config.CARE_TOPIC,
                payload,
                qos=1,
                retain=False
            )

            print("Publish return code:", result.rc)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print("Care result published successfully.")
            else:
                print("Care result publish FAILED.")

            print("=======================================")

        except Exception as e:
            print("Care MQTT publish failed:")
            print(e)

    def publish_weather_result(self, weather_result):
        """Publish weather information to the Node-RED dashboard."""

        try:
            if not weather_result:
                print("Weather result is empty. Nothing to publish.")
                return

            payload = {
                "device_id": "greenpulse-01",
                "type": "weather_update",
                "timestamp": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ",
                    time.gmtime()
                ),
                "weather": weather_result,
            }

            result = self.client.publish(
                "greenpulse/device01/weather",
                json.dumps(payload),
                qos=1,
                retain=False,
            )

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print("Weather result published to Node-RED.")
                print("Weather payload:", json.dumps(payload))
            else:
                print("Failed to publish weather result.")

        except Exception as e:
            print("Weather MQTT publish failed:")
            print(e)

    # =========================================================
    # PUBLISH WATERING PREDICTION
    # =========================================================

    def publish_prediction_result(self, prediction_result):
        """Publish watering prediction to the Node-RED dashboard."""

        try:
            if not prediction_result:
                prediction_result = {
                    "model_status": "unavailable",
                    "reason": "No prediction result was returned."
                }

            payload = {
                "device_id": "greenpulse-01",
                "type": "watering_prediction",
                "timestamp": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ",
                    time.gmtime()
                ),
                "prediction": prediction_result
            }

            topic = "greenpulse/device01/prediction"

            result = self.client.publish(
                topic,
                json.dumps(payload),
                qos=1,
                retain=False
            )

            print("\n========== PREDICTION MQTT PUBLISH ==========")
            print("Topic:", topic)
            print("Payload:", json.dumps(payload))

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print("Watering prediction published successfully.")
            else:
                print(
                    "Watering prediction publish failed. "
                    f"MQTT code: {result.rc}"
                )

            print("==============================================")

        except Exception as e:
            print("Prediction MQTT publishing failed:")
            print(e)

    def publish_notification_result(self, pipeline_result):
        """
        Publish email delivery status and recent care emails
        to the GreenPulse Node-RED dashboard.
        """

        try:
            email_delivery = pipeline_result.get(
                "email_delivery", {}
            )

            care_emails = pipeline_result.get(
                "care_emails", {}
            )

            care_result = pipeline_result.get(
                "care", {}
            )

            payload = {
                "device_id": "greenpulse-01",
                "type": "care_notification",
                "timestamp": email_delivery.get(
                    "timestamp"
                ),
                "urgency": care_result.get(
                    "urgency", "UNKNOWN"
                ),
                "recommendation": care_result.get(
                    "recommendation", ""
                ),
                "email_delivery": {
                    "status": email_delivery.get(
                        "status", "unknown"
                    ),
                    "sent": email_delivery.get(
                        "sent", False
                    ),
                    "subject": email_delivery.get(
                        "subject"
                    ),
                    "recipient": email_delivery.get(
                        "recipient"
                    ),
                    "message_id": email_delivery.get(
                        "message_id"
                    ),
                },
                "recent_care_emails": care_emails.get(
                    "emails", []
                ),
                "email_fetch_status": care_emails.get(
                    "status", "unknown"
                ),
            }

            result = self.client.publish(
                "greenpulse/device01/notifications",
                json.dumps(payload),
                qos=1,
                retain=False,
            )

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(
                    "Notification result published to Node-RED."
                )
            else:
                print(
                    "Failed to publish notification result. "
                    f"MQTT code: {result.rc}"
                )

        except Exception as exc:
            print("Notification MQTT publishing failed:")
            print(exc)

    # =========================================================
    # DISCONNECT
    # =========================================================

    def on_disconnect(
        self,
        client,
        userdata,
        rc
    ):

        print()
        print(
            "AWS IoT MQTT disconnected."
        )

        print(
            "Disconnect code:",
            rc
        )