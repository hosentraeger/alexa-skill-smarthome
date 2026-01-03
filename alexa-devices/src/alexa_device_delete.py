import boto3, json, os
table = boto3.resource("dynamodb").Table(os.environ["DEVICE_TABLE"])

def delete_device(event, context=None):
    device_id = event["pathParameters"]["device_id"]
    table.delete_item(Key={"device_id": device_id})
    return {
        "statusCode": 200,
        "headers": {"Access-Control-Allow-Origin": os.environ.get("CORS_DOMAIN", "*")},
        "body": json.dumps({"device_id": device_id, "message": "deleted"})
    }