import boto3
import os
import json
import time
import requests
from boto3.dynamodb.conditions import Key
from datetime import datetime, timezone

# Initialisierung
table = boto3.resource("dynamodb").Table(os.environ["DEVICE_TABLE"])
ALEXA_BEARER_TOKEN = os.environ["ALEXA_BEARER_TOKEN"]
ALEXA_EVENTS_URL = "https://api.amazonalexa.com/v3/events"

def send_change_report(device_id, namespace, name, value):
    """Sendet ein ChangeReport Event an Alexa."""
    timestamp = datetime.now(timezone.utc).isoformat()
    event_payload = {
        "event": {
            "header": {
                "namespace": "Alexa",
                "name": "ChangeReport",
                "payloadVersion": "3",
                "messageId": f"change-{int(time.time()*1000)}"
            },
            "endpoint": {
                "endpointId": device_id
            },
            "payload": {
                "change": {
                    "cause": {
                        "type": "PHYSICAL_INTERACTION"
                    },
                    "properties": [
                        {
                            "namespace": namespace,
                            "name": name,
                            "value": value,
                            "timeOfSample": timestamp,
                            "uncertaintyInMilliseconds": 500
                        }
                    ]
                }
            }
        }
    }

    headers = {
        "Authorization": f"Bearer {ALEXA_BEARER_TOKEN}",
        "Content-Type": "application/json"
    }

    resp = requests.post(ALEXA_EVENTS_URL, headers=headers, json=event_payload)
    if resp.status_code == 202:
        print(f"ChangeReport erfolgreich an Alexa gesendet: {device_id} {name}={value}")
    else:
        print(f"Fehler beim Senden des ChangeReport: {resp.status_code} {resp.text}")

def lambda_handler(event, context):
    try:
        # Event von der IoT Rule (Topic: alexa/+/state)
        item_name = event.get("item_name")
        new_state = event.get("state")

        if not item_name or new_state is None:
            print("Fehler: item_name oder state fehlt im Event")
            return

        # 1. Schritt: Suche nach der UUID (device_id) via item_name
        response = table.query(
            IndexName="item-name-index",
            KeyConditionExpression=Key("item_name").eq(item_name)
        )

        items = response.get("Items", [])
        if not items:
            print(f"Geräte mit item_name '{item_name}' nicht in Datenbank gefunden.")
            return

        real_id = items[0]["device_id"]

        # 2. Schritt: Update des Status mit dem echten Primary Key
        table.update_item(
            Key={"device_id": real_id},
            UpdateExpression="SET #s = :val",
            ExpressionAttributeNames={"#s": "state"},
            ExpressionAttributeValues={":val": new_state}
        )
        print(f"Erfolg: {dev_name} (ID: {real_id}) auf '{new_state}' aktualisiert.")

        # 3. Schritt: ChangeReport an Alexa senden
        # Hier Namespace/Name anpassen je nach Capability:
        # z.B. PowerController -> powerState, ModeController -> mode, BrightnessController -> brightness
        # In deinem Fall nehmen wir einfach powerState für Beispiel
        send_change_report(real_id, "Alexa.TemperatureSensor", "temperature", float(new_state))


    except Exception as e:
        print(f"Fehler: {str(e)}")
        raise e
