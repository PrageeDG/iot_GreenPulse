import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Key

import config


class DynamoDBService:

    def __init__(self):
        self.dynamodb = boto3.resource(
            "dynamodb",
            region_name=config.AWS_REGION
        )

        self.table = self.dynamodb.Table(
            config.DYNAMODB_TABLE
        )

    def save_sensor_reading(self, sensor_data):

        self.table.put_item(
            Item={
                "device_id": sensor_data.device_id,
                "timestamp": sensor_data.timestamp,
                "temperature": Decimal(
                    str(sensor_data.temperature)
                ),
                "humidity": Decimal(
                    str(sensor_data.humidity)
                ),
                "soil_moisture": Decimal(
                    str(sensor_data.soil_moisture)
                ),
                "light": Decimal(
                    str(sensor_data.light)
                )
            }
        )

        print("DynamoDB: Sensor reading stored successfully.")

    def get_recent_sensor_readings(
        self,
        device_id="greenpulse-01",
        limit=1000
    ):
        """
        Retrieve recent sensor readings for one device.

        Results are returned newest first.
        """

        response = self.table.query(
            KeyConditionExpression=Key(
                "device_id"
            ).eq(device_id),
            ScanIndexForward=False,
            Limit=limit
        )

        readings = response.get("Items", [])

        # Continue retrieving older pages if necessary.
        while (
            "LastEvaluatedKey" in response
            and len(readings) < limit
        ):
            remaining = limit - len(readings)

            response = self.table.query(
                KeyConditionExpression=Key(
                    "device_id"
                ).eq(device_id),
                ScanIndexForward=False,
                Limit=remaining,
                ExclusiveStartKey=response[
                    "LastEvaluatedKey"
                ]
            )

            readings.extend(
                response.get("Items", [])
            )

        print(
            f"DynamoDB: Retrieved {len(readings)} "
            f"historical readings."
        )

        return readings