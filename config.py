import os

from dotenv import load_dotenv

load_dotenv()





AWS_IOT_ENDPOINT = "a1nrnv5x66u1mb-ats.iot.us-east-1.amazonaws.com"
DYNAMODB_TABLE = "GreenPulseSensorReadings"
AWS_REGION = "us-east-1"

CLIENT_ID = "GreenPulse-Backend"

SENSOR_TOPIC = "greenpulse/device01/sensors"
STATUS_TOPIC = "greenpulse/device01/status"
CARE_TOPIC = "greenpulse/device01/care"
WEATHER_TOPIC = "greenpulse/device01/weather"
NOTIFICATION_TOPIC = "greenpulse/device01/notifications"

ROOT_CA = "aws-certificates/AmazonRootCA1.pem"
CERTIFICATE = "aws-certificates/device-certificate.pem.crt"
PRIVATE_KEY = "aws-certificates/private.pem.key"

CITY_NAME = os.getenv("CITY_NAME", "Colombo")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")
LLM_MODE = os.getenv("LLM_MODE")