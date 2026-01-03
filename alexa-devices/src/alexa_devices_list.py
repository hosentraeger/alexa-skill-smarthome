import boto3, json, os
from decimal import Decimal

table = boto3.resource("dynamodb").Table(os.environ["DEVICE_TABLE"])

def decimal_default(obj):
    if isinstance(obj, Decimal):
        # Wenn es eine ganze Zahl ist, als Int, sonst als Float
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def list_devices(event, context=None):
    items = table.scan().get("Items", [])

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        # Hier ist die entscheidende Änderung: default=decimal_default
        "body": json.dumps(items, default=decimal_default)
    }
