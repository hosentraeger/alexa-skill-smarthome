import boto3, json, os, uuid
from decimal import Decimal

table = boto3.resource("dynamodb").Table(os.environ["DEVICE_TABLE"])

def add_device(event, context=None):
    try:
        body = json.loads(event.get("body") or "{}", parse_float=Decimal)
    except Exception as e:
        return {"statusCode": 400, "body": json.dumps({"error": "Invalid JSON"})}

    new_id = str(uuid.uuid4())
    
    item = {
        "device_id": new_id,
        "friendly_name": body.get("friendly_name"),
        "description": body.get("description", ""),
        "device_category": body.get("device_category"),
        "capabilities": body.get("capabilities", []),
        "proactivelyReported": body.get("proactivelyReported", False),
        "retrievable": body.get("retrievable", False),
        "state": body.get("state", ""),
        "handle_generic": body.get("OpenHABHandleGeneric", True),
        "enabled": body.get("enabled", True),
        "item_name": body.get("item_name", "")
    }
    
    table.put_item(Item=item)
    
    return {
        "statusCode": 201,
        "headers": {
            "Access-Control-Allow-Origin": os.environ.get("CORS_DOMAIN", "*"),
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
        },
        "body": json.dumps({"device_id": new_id, "message": "created"})
    }