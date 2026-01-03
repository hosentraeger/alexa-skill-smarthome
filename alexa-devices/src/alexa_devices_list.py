import boto3, json, os
table = boto3.resource("dynamodb").Table(os.environ["DEVICE_TABLE"])

def list_devices(event, context=None):
    items = table.scan().get("Items", [])
    # Rückgabe unverändert, capabilities bleiben Array
    return {
        "statusCode": 200,
        "headers": {"Access-Control-Allow-Origin": os.environ.get("CORS_DOMAIN", "*")},
        "body": json.dumps(items)
    }