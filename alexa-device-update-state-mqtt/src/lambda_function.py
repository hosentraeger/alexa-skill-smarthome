import os
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

# Logger & Konfiguration
logger = logging.getLogger()
logger.setLevel(logging.INFO)

ALEXA_EVENTS_URL = os.environ.get("ALEXA_EVENTS_URL", "https://api.eu.amazonalexa.com/v3/events")
CLIENT_ID = os.environ.get("ALEXA_CLIENT_ID")
CLIENT_SECRET = os.environ.get("ALEXA_CLIENT_SECRET")
DEVICE_TABLE = os.environ.get("DEVICE_TABLE", "smarthome_devices")

ssm = boto3.client("ssm")
table = boto3.resource("dynamodb").Table(DEVICE_TABLE)


def float_to_decimal(obj):
    """Konvertiert Floats/Dicts rekursiv für DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: float_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [float_to_decimal(i) for i in obj]
    return obj


def get_valid_access_token():
    try:
        res = ssm.get_parameter(Name="/alexa/access_token", WithDecryption=True)
        return res["Parameter"]["Value"]
    except Exception:
        return refresh_alexa_token()


def refresh_alexa_token():
    logger.info("Refreshe LWA Token...")
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


def attempt_send(token, endpoint_id, properties):
    """Sendet ein ChangeReport Event an das Alexa Gateway."""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

    # Der ChangeReport Aufbau
    payload = {
        "context": {
            "properties": []  # Hier könnten zusätzliche Zustände stehen
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
                    "properties": properties  # Hier kommen die konvertierten Props rein
                }
            }
        }
    }

    req = urllib.request.Request(ALEXA_EVENTS_URL, data=json.dumps(payload).encode('utf-8'), method='POST')
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")

    logger.info(f"Sende ChangeReport für {endpoint_id} an Alexa...")
    with urllib.request.urlopen(req) as response:
        return response.getcode()


def lambda_handler(event, context):
    try:
        item_name = event.get("item_name")
        raw_state_oh = event.get("state")  # z.B. "OPEN", "ON", 22.5

        if not item_name or raw_state_oh is None:
            logger.error("Event unvollständig.")
            return

        # 1. Device laden
        res = table.query(IndexName="item-name-index", KeyConditionExpression=Key("item_name").eq(item_name))
        items = res.get("Items", [])
        if not items:
            logger.warning(f"Item {item_name} unbekannt.")
            return

        record = items[0]
        endpoint_id = record["device_id"]

        # 2. ÜBERSETZUNG: Hardware -> Alexa
        device = AlexaDevice(record)
        alexa_updates = {}

        # Wir fragen alle Controller des Geräts, wer dieses Update versteht
        for controller in device.controllers:
            update = controller.handle_update({"state": raw_state_oh})
            if update:
                alexa_updates.update(update)

        if not alexa_updates:
            logger.info("Keine Alexa-relevante Änderung erkannt.")
            return

        # 3. DB UPDATE (nur wenn sich wirklich was geändert hat)
        new_state_ddb = float_to_decimal(alexa_updates)
        table.update_item(
            Key={"device_id": endpoint_id},
            UpdateExpression="SET #s = :val",
            ExpressionAttributeNames={"#s": "state"},
            ExpressionAttributeValues={":val": new_state_ddb}
        )

        # 4. CHANGE REPORT BAUEN
        # Wir müssen die alexa_updates in das Property-Format von Alexa bringen
        device.raw_state.update(alexa_updates)  # Device-State lokal aktualisieren
        all_props = device.get_all_properties()

        # Wir filtern nur die Properties, die wir gerade geändert haben
        # (Einfacher MVP-Check: Ist der Name der Property im alexa_updates Dict?)
        changed_props_for_alexa = []
        for p in all_props:
            if p["name"] in alexa_updates:
                p["timeOfSample"] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                p["uncertaintyInMilliseconds"] = 0
                changed_props_for_alexa.append(p)

        if not changed_props_for_alexa:
            return

        # 5. SENDEN
        token = get_valid_access_token()
        try:
            status = attempt_send(token, endpoint_id, changed_props_for_alexa)
            logger.info(f"Alexa Gateway Status: {status}")
        except urllib.error.HTTPError as e:
            if e.code == 401:
                token = refresh_alexa_token()
                attempt_send(token, endpoint_id, changed_props_for_alexa)
            else:
                raise e

    except Exception as e:
        logger.error(f"Fehler: {str(e)}")