import boto3, json, os, logging
from decimal import Decimal

# Logging konfigurieren
logger = logging.getLogger()
logger.setLevel(logging.INFO)

table = boto3.resource("dynamodb").Table(os.environ["DEVICE_TABLE"])

def update_device(event, context=None):
    device_id = event.get("pathParameters", {}).get("device_id")
    raw_body = event.get("body") or "{}"
    
    # 1. Log: Eingehender Request
    logger.info(f"Update Request for ID: {device_id}")
    logger.info(f"Raw Body: {raw_body}")

    try:
        body = json.loads(raw_body, parse_float=Decimal)
    except Exception as e:
        logger.error(f"JSON Parse Error: {str(e)}")
        return {"statusCode": 400, "body": json.dumps({"error": "Invalid JSON"})}

    update_parts = []
    attr_values = {}
    attr_names = {}

    # Map: Frontend-Key -> Platzhalter
    fields = {
        "friendly_name": ":f",
        "description": ":d",
        "device_category": ":c",
        "capabilities": ":cap",
        "proactivelyReported": ":pr",
        "retrievable": ":ret",
        "state": ":s",
        "OpenHABHandleGeneric": ":hg",
        "enabled": ":e",
        "item_name": ":n"
    }

    # Reservierte Wörter (WICHTIG: 'enabled' und 'state' sind reserviert!)
    reserved_or_special = ("state", "capabilities", "description", "enabled", "device_category")

    for field, placeholder in fields.items():
        if field in body:
            # 2. Log: Gefundene Felder
            logger.info(f"Field found in body: {field} = {body[field]}")
            
            if field in reserved_or_special:
                update_parts.append(f"#{field} = {placeholder}")
                attr_names[f"#{field}"] = field
            else:
                update_parts.append(f"{field} = {placeholder}")
            
            attr_values[placeholder] = body[field]
        else:
            # 3. Log: Vermisste Felder (nur zur Info)
            logger.debug(f"Field {field} not in body")

    if not update_parts:
        logger.warning("No valid fields found to update!")
        return {"statusCode": 400, "body": json.dumps({"error": "No valid fields in body"})}

    update_params = {
        "Key": {"device_id": device_id},
        "UpdateExpression": "SET " + ", ".join(update_parts),
        "ExpressionAttributeValues": attr_values
    }
    
    if attr_names:
        update_params["ExpressionAttributeNames"] = attr_names

    # 4. Log: Finale DynamoDB Parameter
    logger.info(f"DynamoDB Update Params: {json.dumps(update_params, default=str)}")

    try:
        response = table.update_item(**update_params)
        logger.info(f"DynamoDB Success: {json.dumps(response, default=str)}")
    except Exception as e:
        logger.error(f"DynamoDB Exception: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "application/json"
        },
        "body": json.dumps({"message": "updated", "id": device_id})
    }