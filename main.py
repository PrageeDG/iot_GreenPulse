from services.mqtt_service import MQTTService


def main():

    print()
    print("========================================")
    print("      GREENPULSE UNIFIED BACKEND")
    print("========================================")

    mqtt_service = MQTTService()

    mqtt_service.connect()

    print()
    print("Backend is running.")
    print("Waiting for sensor data...")

    try:

        while True:

            pass

    except KeyboardInterrupt:

        print()
        print("Shutting down GreenPulse backend...")


if __name__ == "__main__":
    main()