#!/usr/bin/env python3
import json
import sys
import boto3
from alexa_device import AlexaDevice
from alexa.skills.smarthome.alexa_response import AlexaResponse

def get_real_device(endpoint_id):
    """Lädt das Gerät live aus DynamoDB für einen echten End-to-End Test."""
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    table = dynamodb.Table('smarthome_devices')
    
    response = table.get_item(Key={'device_id': endpoint_id})
    return response.get('Item')

def main():
    # 1. JSON von stdin lesen
    try:
        if sys.stdin.isatty():
            print("Warte auf JSON-Input via Pipe (z.B. echo '...' | python3 test_control.py)")
            return
            
        input_data = json.load(sys.stdin)
        directive = input_data.get('directive')
        if not directive:
            print("Fehler: Kein 'directive' Key im JSON gefunden.")
            return
    except json.JSONDecodeError as e:
        print(f"Fehler beim Parsen des JSON: {e}")
        return

    header = directive['header']
    endpoint_id = directive['endpoint']['endpointId']
    
    # 2. Gerät laden (Live aus DB oder Mock)
    record = get_real_device(endpoint_id)
    
    if not record:
        print(f"Warnung: Gerät {endpoint_id} nicht in DB gefunden. Nutze Mock-Daten.")
        record = {
            "device_id": endpoint_id,
            "friendly_name": "Testgerät",
            "capabilities": ["PowerController", "BrightnessController", "SpeakerController", "ModeController"],
            "state": {"power": "OFF", "brightness": 0, "volume": 10, "mode": "STOP"}
        }

    # 3. AlexaDevice initialisieren
    device = AlexaDevice(record)
    
    # 4. Befehl verarbeiten
    mqtt_payload = device.execute_directive(directive)
    
    # 5. Output generieren
    print(f"\n{'='*60}")
    print(f"DIREKTIVE: {header['namespace']} :: {header['name']}")
    print(f"GERÄT:     {device.friendly_name} ({endpoint_id})")
    print(f"{'='*60}")

    if mqtt_payload:
        print(f"\n[MQTT] Sende an Topic: devices/{endpoint_id}/set")
        print(f"[MQTT] Payload: {json.dumps(mqtt_payload, indent=2)}")
    
    # 6. Alexa Response bauen
    adr = AlexaResponse(
        correlation_token=header.get('correlationToken'),
        endpoint_id=endpoint_id,
        token=directive['endpoint']['scope']['token']
    )
    
    for prop in device.get_all_properties():
        adr.add_context_property(**prop)

    print(f"\n[ALEXA] Response JSON:")
    print(json.dumps(adr.get(), indent=2))
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()