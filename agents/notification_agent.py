import os
import base64

from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Dict, Any

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


# =====================================================
# GMAIL CONFIGURATION
# =====================================================

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


class NotificationAgent:
    """
    GreenPulse Notification Agent.

    Responsibilities:
    1. Send care-summary emails.
    2. Retrieve recent GreenPulse care emails.
    3. Return notification status for MQTT / Node-RED.
    """

    def __init__(self):
        self.token_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "token.json",
        )

        self.recipient = os.getenv("CARE_EMAIL_TO")

        # Track the last successfully emailed care decision
        self.last_sent_signature = None

    # =================================================
    # GMAIL AUTHENTICATION
    # =================================================

    def _get_gmail_service(self):
        if not os.path.exists(self.token_path):
            raise FileNotFoundError(
                "token.json was not found. "
                "Run setup_gmail.py to authorize Gmail."
            )

        creds = Credentials.from_authorized_user_file(
            self.token_path,
            GMAIL_SCOPES,
        )

        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())

                with open(
                    self.token_path,
                    "w",
                    encoding="utf-8",
                ) as token_file:
                    token_file.write(creds.to_json())

            else:
                raise RuntimeError(
                    "Gmail credentials are invalid. "
                    "Run setup_gmail.py again."
                )

        return build(
            "gmail",
            "v1",
            credentials=creds,
            cache_discovery=False,
        )

    # =================================================
    # SEND CARE SUMMARY EMAIL
    # =================================================

    def send_care_email(
        self,
        care_result: Dict[str, Any],
        sensor_data: Any,
        weather_data: Dict[str, Any] = None,
    ) -> Dict[str, Any]:

        if not self.recipient:
            return {
                "status": "not_configured",
                "sent": False,
                "subject": None,
                "message": (
                    "CARE_EMAIL_TO is missing from the "
                    "backend environment configuration."
                ),
            }

        weather_data = weather_data or {}

        urgency = str(
            care_result.get("urgency", "UNKNOWN")
        ).upper()

        recommendation = care_result.get(
            "recommendation",
            "Monitor the plant conditions.",
        )

        reason = care_result.get(
            "reason",
            "No additional explanation was provided.",
        )

        watering_required = care_result.get(
            "watering_required",
            False,
        )

        # =====================================================
        # DUPLICATE EMAIL PREVENTION
        # =====================================================

        signature = (
            urgency,
            bool(watering_required),
        )

        if signature == self.last_sent_signature:
            print("Duplicate care notification detected. Email skipped.")

            return {
                "status": "skipped_duplicate",
                "sent": False,
                "subject": None,
                "recipient": self.recipient,
                "message": (
                    "The care decision has not changed. "
                    "Duplicate email skipped."
                ),
                "urgency": urgency,
            }

        temperature = sensor_data.temperature
        humidity = sensor_data.humidity
        soil_moisture = sensor_data.soil_moisture
        light = sensor_data.light

        timestamp = datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%d %H:%M:%S UTC")

        subject = (
            f"[GreenPulse] {urgency.title()} "
            "Plant Care Summary"
        )

        weather_description = weather_data.get(
            "description",
            "Weather information unavailable.",
        )

        weather_temperature = weather_data.get(
            "temperature"
        )

        weather_line = weather_description

        if weather_temperature is not None:
            weather_line += (
                f" ({weather_temperature}°C)"
            )

        email_body = f"""
GREENPULSE PLANT CARE SUMMARY
=============================

Plant: Indoor Banyan (Ficus microcarpa)
Device: {sensor_data.device_id}
Generated: {timestamp}

CARE STATUS
-----------
Urgency: {urgency}

CURRENT SENSOR READINGS
-----------------------
Soil moisture: {soil_moisture}%
Temperature: {temperature}°C
Humidity: {humidity}%
Light: {light} lux

CARE RECOMMENDATION
-------------------
{recommendation}

REASON
------
{reason}

WATERING DECISION
-----------------
{"Watering recommended" if watering_required else "Watering not currently recommended"}

WEATHER CONTEXT
---------------
{weather_line}

This care summary was generated by GreenPulse.
Use the sensor readings and recommendation as guidance,
and check the actual soil condition before watering.
""".strip()

        try:
            service = self._get_gmail_service()

            message = EmailMessage()

            message["To"] = self.recipient
            message["Subject"] = subject

            message.set_content(email_body)

            encoded_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode("utf-8")

            result = (
                service.users()
                .messages()
                .send(
                    userId="me",
                    body={"raw": encoded_message},
                )
                .execute()
            )

            self.last_sent_signature = signature

            print("GreenPulse care email sent.")
            print(f"Recipient: {self.recipient}")
            print(f"Subject: {subject}")
            print(f"Gmail message ID: {result.get('id')}")

            return {
                "status": "sent",
                "sent": True,
                "subject": subject,
                "recipient": self.recipient,
                "message_id": result.get("id"),
                "timestamp": timestamp,
                "summary": recommendation,
                "urgency": urgency,
            }

        except Exception as exc:
            print("GreenPulse care email failed:")
            print(exc)

            return {
                "status": "failed",
                "sent": False,
                "subject": subject,
                "timestamp": timestamp,
                "summary": recommendation,
                "urgency": urgency,
                "error": str(exc),
            }

    # =================================================
    # FETCH RECENT CARE EMAILS
    # =================================================

    def fetch_care_emails(
        self,
        max_results: int = 10,
    ) -> Dict[str, Any]:

        try:
            service = self._get_gmail_service()

            # Retrieve GreenPulse care-summary emails.
            query = (
                'from:me subject:GreenPulse '
                'subject:Care newer_than:30d'
            )

            response = (
                service.users()
                .messages()
                .list(
                    userId="me",
                    q=query,
                    maxResults=max_results,
                )
                .execute()
            )

            messages = response.get("messages", [])

            care_emails = []

            for item in messages:

                message = (
                    service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=item["id"],
                        format="metadata",
                        metadataHeaders=[
                            "Subject",
                            "To",
                            "Date",
                        ],
                    )
                    .execute()
                )

                headers = message.get(
                    "payload", {}
                ).get("headers", [])

                header_values = {
                    header["name"].lower(): header["value"]
                    for header in headers
                }

                care_emails.append({
                    "id": message.get("id"),
                    "subject": header_values.get(
                        "subject",
                        "GreenPulse Care Notification",
                    ),
                    "recipient": header_values.get(
                        "to",
                        "",
                    ),
                    "date": header_values.get(
                        "date",
                        "",
                    ),
                    "snippet": message.get(
                        "snippet",
                        "",
                    ),
                })

            return {
                "status": "success",
                "count": len(care_emails),
                "emails": care_emails,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

        except Exception as exc:
            print("Failed to fetch GreenPulse care emails:")
            print(exc)

            return {
                "status": "failed",
                "count": 0,
                "emails": [],
                "error": str(exc),
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }