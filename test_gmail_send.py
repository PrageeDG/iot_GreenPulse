import os
import base64

from email.message import EmailMessage
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

creds = Credentials.from_authorized_user_file(
    "token.json",
    SCOPES
)

if not creds.valid:
    raise RuntimeError(
        "Gmail credentials are invalid. "
        "Run setup_gmail.py again."
    )

recipient = input("Enter your email address: ").strip()

message = EmailMessage()
message["To"] = recipient
message["Subject"] = "GreenPulse Gmail Integration Test"
message.set_content(
    "GreenPulse Gmail integration is working.\n\n"
    "The system can now send plant-care notification emails."
)

encoded_message = base64.urlsafe_b64encode(
    message.as_bytes()
).decode()

service = build("gmail", "v1", credentials=creds)

result = service.users().messages().send(
    userId="me",
    body={"raw": encoded_message}
).execute()

print("Email sent successfully!")
print("Gmail message ID:", result["id"])