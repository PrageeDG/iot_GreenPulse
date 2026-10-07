import json
import boto3

from awscrt import mqtt
from awsiot import mqtt_connection_builder
from datetime import datetime
from decimal import Decimal

import config


def on_connection_interrupted(connection, error, **kwargs):
    print()
    print("MQTT connection interrupted")
    print(f"Error: {error}")


def on_connection_resumed(connection, return_code, session_present, **kwargs):
    print()
    print("MQTT connection resumed")
    print(f"Return code: {return_code}")
    print(f"Session present: {session_present}")

    if return_code == mqtt.ConnectReturnCode.ACCEPTED:

        print("Resubscribing to sensor topic...")

        connection.subscribe(
            topic=config.SENSOR_TOPIC,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=on_sensor_message,
        )
dynamodb = boto3.resource(
    "dynamodb",
    region_name=config.AWS_REGION
)

sensor_table = dynamodb.Table(
    config.DYNAMODB_TABLE
)

def on_sensor_message(topic, payload, **kwargs):

    print()
    print("========================================")
    print("       SENSOR MESSAGE RECEIVED")
    print("========================================")

    print(f"Topic: {topic}")

    try:

        data = json.loads(payload)

        timestamp_str = data.get("timestamp")

        if timestamp_str:
            try:
                sensor_time = datetime.fromisoformat(
                    timestamp_str.replace("Z", "+00:00")
                )
                print(f"Timestamp (UTC): {sensor_time}")
            except ValueError:
                print(f"Invalid timestamp: {timestamp_str}")
                sensor_time = None

        else:
            print("Timestamp missing")
            sensor_time = None

        print("Sensor data:")

        print(
            json.dumps(
                data,
                indent=2
            )
        )

        # -----------------------------------------
        # Individual values
        # -----------------------------------------

        device_id = data.get("device_id")
        temperature = data.get("temperature")
        humidity = data.get("humidity")
        soil_moisture = data.get("soil_moisture")
        light = data.get("light")

        print()
        print(f"Device: {device_id}")
        print(f"Temperature: {temperature} °C")
        print(f"Humidity: {humidity} %")
        print(f"Soil moisture: {soil_moisture} %")
        print(f"Light: {light} lux")

    except json.JSONDecodeError:

        print("Received non-JSON payload:")
        print(payload)

    print("========================================")

    try:
        sensor_table.put_item(
    Item={
        "device_id": device_id,
        "timestamp": timestamp_str,
        "temperature": Decimal(str(temperature)),
        "humidity": Decimal(str(humidity)),
        "soil_moisture": Decimal(str(soil_moisture)),
        "light": Decimal(str(light))
        }
    )

        print("DynamoDB: Sensor reading stored successfully.")

    except Exception as e:
    
        print("DynamoDB write failed:")
        print(e)


def main():

    print("========================================")
    print("       GREENPULSE CLOUD BACKEND")
    print("========================================")

    print()
    print("Connecting to AWS IoT Core...")

    mqtt_connection = mqtt_connection_builder.mtls_from_path(

        endpoint=config.AWS_IOT_ENDPOINT,

        cert_filepath=config.CERTIFICATE,

        pri_key_filepath=config.PRIVATE_KEY,

        ca_filepath=config.ROOT_CA,

        client_id=config.CLIENT_ID,

        clean_session=False,

        keep_alive_secs=30,

    )

    mqtt_connection.on_connection_interrupted = (
        on_connection_interrupted
    )

    mqtt_connection.on_connection_resumed = (
        on_connection_resumed
    )

    connect_future = mqtt_connection.connect()

    connect_future.result()

    print("Connected to AWS IoT Core!")

    print()
    print("Subscribing to:")
    print(config.SENSOR_TOPIC)

    subscribe_future, packet_id = mqtt_connection.subscribe(

        topic=config.SENSOR_TOPIC,

        qos=mqtt.QoS.AT_LEAST_ONCE,

        callback=on_sensor_message,

    )

    subscribe_future.result()

    print("Successfully subscribed!")

    print()
    print("Waiting for sensor data...")
    print("Press Ctrl+C to stop.")

    try:

        while True:

            pass

    except KeyboardInterrupt:

        print()
        print("Disconnecting...")

        disconnect_future = mqtt_connection.disconnect()

        disconnect_future.result()

        print("Disconnected.")


if __name__ == "__main__":
    main()