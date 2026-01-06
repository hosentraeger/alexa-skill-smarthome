import urllib.request
import json
import uuid
import os
import sys
from datetime import datetime, timezone

# --- DATEN AUS UMGEBUNG ---
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
ENDPOINT_ID = "f4442138-ecb6-4035-97c0-ca44961bc1ec"

if not ACCESS_TOKEN:
    print("FEHLER: Die Umgebungsvariable $ACCESS_TOKEN ist nicht gesetzt!")
    sys.exit(1)

def get_utc_timestamp():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

url = "https://api.eu.amazonalexa.com/v3/events"

# Struktur korrigiert: context und event auf oberster Ebene
data = {
    "context": {
        "properties": [
            {
                "namespace": "Alexa.EndpointHealth",
                "name": "connectivity",
                "value": {"value": "OK"},
                "timeOfSample": get_utc_timestamp(),
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
        "endpoint": {
            "scope": {
                "type": "BearerToken",
                "token": ACCESS_TOKEN
            },
            "endpointId": ENDPOINT_ID
        },
        "payload": {
            "change": {
                "cause": {"type": "PERIODIC_POLL"},
                "properties": [
                    {
                        "namespace": "Alexa.TemperatureSensor",
                        "name": "temperature",
                        "value": {"value": 22.5, "scale": "CELSIUS"},
                        "timeOfSample": get_utc_timestamp(),
                        "uncertaintyInMilliseconds": 0
                    }
                ]
            }
        }
    }
}

req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), method='POST')
req.add_header("Authorization", f"Bearer {ACCESS_TOKEN}")
req.add_header("Content-Type", "application/json")

data=json.dumps(data).encode('utf-8')
print(f"payload: {data}")
print(f"Sende ChangeReport für {ENDPOINT_ID}...")

try:
    with urllib.request.urlopen(req) as response:
        print(f"Status: {response.getcode()} (Erfolg!)")
        print(f"Response: {response.read().decode('utf-8')}")
except urllib.error.HTTPError as e:
    print(f"Error {e.code}: {e.read().decode('utf-8')}")
except Exception as e:
    print(f"Unerwarteter Fehler: {e}")
