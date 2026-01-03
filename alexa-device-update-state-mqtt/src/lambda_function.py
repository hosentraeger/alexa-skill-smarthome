import os
import time
import json
import logging
import uuid
import urllib.request
import urllib.parse
import urllib.error
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal
from datetime import datetime, timezone

# Eigene Klassen importieren
from alexa_device import AlexaDevice

# Konfiguration
ALEXA_EVENTS_URL = os.environ.get(
    "ALEXA_EVENTS_URL",
    "https://api.eu.amazonalexa.com/v3/events"
)
CLIENT_ID = os.environ.get("ALEXA_CLIENT_ID")
CLIENT_SECRET = os.environ.get("ALEXA_CLIENT_SECRET")
DEVICE_TABLE = os.environ.get("DEVICE_TABLE", "smarthome_devices")

# Logger & Clients
logger = logging.getLogger()
logger.setLevel(logging.INFO)
ssm = boto3.client("ssm")
table = boto3.resource("dynamodb").Table(DEVICE_TABLE)


def float_to_decimal(obj):
    """Konvertiert Floats rekursiv in Decimals für DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: float_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [float_to_decimal(i) for i in obj]
    return obj


def get_valid_access_token():
    """Holt den aktuellen Token aus dem SSM oder erzwingt Refresh."""
    try:
        res = ssm.get_parameter(Name="/alexa/access_token", WithDecryption=True)
        return res["Parameter"]["Value"]
    except Exception:
        return refresh_alexa_token()


def refresh_alexa_token():
    """Erneuert den Token via LWA (Login with Amazon)."""
    logger.info("Starte Token-Refresh via LWA...")
    refresh_token = ssm.get_parameter(Name="/alexa/refresh_token", WithDecryption=True)["Parameter"]["Value"]

    url = "https://api.amazon.com/auth/o2/token"
    params = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }

    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    with urllib.request.urlopen(req) as response:
        res = json.loads(response.read().decode("utf-8"))
        new_at = res["access_token"]
        ssm.put_parameter(Name="/alexa/access_token", Value=new_at, Type="SecureString", Overwrite=True)
        return new_at


def attempt_send(token_to_use, endpoint_id, main_prop):
    """Sendet den ChangeReport an das Alexa Event Gateway."""
    # Zeitstempel mit Millisekunden-Präzision
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

    payload = {
        "context": {
            "properties": [
                {
                    "namespace": "Alexa.EndpointHealth",
                    "name": "connectivity",
                    "value": {"value": "OK"},
                    "timeOfSample": now,
                    "uncertaintyInMilliseconds": 0
                }
            ]
        },
        "event": {
            "header": {
                "namespace": "Alexa",
                "name": "ChangeReport",
                "messageId": str(uuid.uuid4()),
                "payloadVersion": "3"
            },
            "endpoint": {"endpointId": endpoint_id},
            "payload": {
                "change": {
                    "cause": {"type": "PHYSICAL_INTERACTION"},
                    "properties": [
                        {
                            "namespace": main_prop["namespace"],
                            "name": main_prop["name"],
                            "value": main_prop["value"],
                            "timeOfSample": now,
                            "uncertaintyInMilliseconds": 0
                        }
                    ]
                }
            }
        }
    }

    # Instance-Feld für ModeController/RangeController falls vorhanden
    if "instance" in main_prop:
        payload["event"]["payload"]["change"]["properties"][0]["instance"] = main_prop["instance"]

    req = urllib.request.Request(ALEXA_EVENTS_URL, data=json.dumps(payload).encode('utf-8'), method='POST')
    req.add_header("Authorization", f"Bearer {token_to_use}")
    req.add_header("Content-Type", "application/json")
    logger.info("sending http request to %s: %s\n", ALEXA_EVENTS_URL, json.dumps(payload))
    with urllib.request.urlopen(req) as response:
        return response.getcode()


def lambda_handler(event, context):
    try:
        item_name = event.get("item_name")
        new_state_raw = event.get("state")

        if not item_name or new_state_raw is None:
            logger.error("item_name oder state fehlt im Event")
            return

        # 1. DynamoDB: Device via item_name suchen
        response = table.query(
            IndexName="item-name-index",
            KeyConditionExpression=Key("item_name").eq(item_name)
        )
        items = response.get("Items", [])
        if not items:
            logger.warning(f"Item '{item_name}' nicht gefunden.")
            return

        record = items[0]
        endpoint_id = record["device_id"]

        # 2. State für DB konvertieren (Float -> Decimal)
        new_state_ddb = float_to_decimal(new_state_raw)

        # 3. DB Update
        table.update_item(
            Key={"device_id": endpoint_id},
            UpdateExpression="SET #s = :val",
            ExpressionAttributeNames={"#s": "state"},
            ExpressionAttributeValues={":val": new_state_ddb}
        )
        logger.info(f"DB Update Erfolg: {item_name} -> {new_state_raw}")

        # 4. Device Objekt für ChangeReport bauen
        # Wir updaten das record-dict mit dem neuen (raw) state für die Controller
        record['state'] = new_state_raw
        device = AlexaDevice(record)

        changed_properties = device.get_all_properties()
        if not changed_properties:
            logger.info("Keine meldungspflichtigen Properties gefunden.")
            return

        # Senden an Alexa Gateway
        logger.info("Token abholen...")
        access_token = get_valid_access_token()

        for prop in changed_properties:
            try:
                status = attempt_send(access_token, endpoint_id, prop)
                logger.info(f"Alexa Report {endpoint_id} [{prop['name']}]: {status}")
            except urllib.error.HTTPError as e:
                if e.code == 401:
                    logger.info("Token abgelaufen (401). Refreshe...")
                    access_token = refresh_alexa_token()
                    status = attempt_send(access_token, endpoint_id, prop)
                    logger.info(f"Erfolg nach Refresh: {status}")
                else:
                    logger.error(f"HTTP Fehler {e.code}: {e.read().decode()}")
            except Exception as e:
                logger.error(f"Fehler bei Prop {prop['name']}: {str(e)}")

    except Exception as e:
        logger.error(f"Kritischer Fehler: {str(e)}")
        raise e