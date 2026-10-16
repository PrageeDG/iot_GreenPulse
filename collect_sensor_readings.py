
import json
import math
import time

import paho.mqtt.client as mqtt

import config
from models.sensor_data import SensorData
from services.dynamodb_service import DynamoDBService

# ==================================================
# Configuration
# ==================================================

SENSOR_TOPIC = "greenpulse/device01/sensors"
CLIENT_ID = "GreenPulse-DynamoDB-Collector"

db_service = DynamoDBService()

# ==================================================
# Validate and store sensor readings
# ==================================================

def process_sensor_message(payload):
    try:
        data = json.loads(payload)

        required_fields = [
            "device_id",
            "timestamp",
            "temperature",
            "humidity",
            "soil_moisture",
            "light",
        ]

        missing = [
            field for field in required_fields
            if field not in data
        ]

        if missing:
            print(f"Rejected: missing fields {missing}")
            return

        # Convert readings to numeric values.
        temperature = float(data["temperature"])
        humidity = float(data["humidity"])
        soil_moisture = float(data["soil_moisture"])
        light = float(data["light"])

        readings = [
            temperature,
            humidity,
            soil_moisture,
            light,
        ]

        if not all(math.isfinite(value) for value in readings):
            print("Rejected: non-finite sensor reading.")
            return

        if not 0 <= humidity <= 100:
            print("Rejected: humidity outside 0–100%.")
            return

        if not 0 <= soil_moisture <= 100:
            print("Rejected: soil moisture outside 0–100%.")
            return

        if light < 0:
            print("Rejected: negative light reading.")
            return

        sensor_data = SensorData(
            device_id=str(data["device_id"]),
            timestamp=str(data["timestamp"]),
            temperature=temperature,
            humidity=humidity,
            soil_moisture=soil_moisture,
            light=light,
        )

        # Direct DynamoDB write only.
        # No MQTTService or orchestrator is called.
        db_service.save_sensor_reading(sensor_data)

        print(
            "SAVED | "
            f"Time: {sensor_data.timestamp} | "
            f"Soil: {soil_moisture}% | "
            f"Temp: {temperature}°C | "
            f"Humidity: {humidity}% | "
            f"Light: {light} lux"
        )

    except (json.JSONDecodeError, TypeError, ValueError) as error:
        print(f"Rejected malformed sensor message: {error}")

    except Exception as error:
        print(f"Failed to store sensor reading: {error}")

# ==================================================
# MQTT callbacks
# ==================================================

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Connected to AWS IoT Core.")
        client.subscribe(SENSOR_TOPIC, qos=1)
        print(f"Subscribed to: {SENSOR_TOPIC}")
        print("DynamoDB-only collection is running.")
        print("Agent pipeline is NOT running.")
    else:
        print(f"MQTT connection failed: {reason_code}")

def on_message(client, userdata, message):
    process_sensor_message(message.payload.decode("utf-8"))

# ==================================================
# Connect securely to AWS IoT Core
# ==================================================

def main():
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=CLIENT_ID,
        protocol=mqtt.MQTTv311,
    )

    client.on_connect = on_connect
    client.on_message = on_message

    client.tls_set(
        ca_certs=config.ROOT_CA,
        certfile=config.CERTIFICATE,
        keyfile=config.PRIVATE_KEY,
    )

    client.connect(
        config.AWS_IOT_ENDPOINT,
        8883,
        keepalive=60,
    )

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nStopping sensor collection...")
    finally:
        client.disconnect()
        client.loop_stop()
        print("Collector stopped.")

if __name__ == "__main__":
    main()