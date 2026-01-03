import boto3
import json
from alexa_device import AlexaDevice
from alexa.skills.smarthome.alexa_response import AlexaResponse

def test_full_discovery_response():
    # 1. Verbindung zur DynamoDB (Lokal via AWS CLI Credentials)
    # Nutze boto3.resource, damit die Daten automatisch "sauber" (unmarshalled) sind
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1') 
    table = dynamodb.Table('smarthome_devices')

    # 2. Initialisierung der Alexa Response für Discovery
    # Die Header-Daten (messageId, namespace, name) werden in der __init__ gesetzt
    adr = AlexaResponse(namespace="Alexa.Discovery", name="Discover.Response")

    print("--- Starte Discovery Simulation ---")

    try:
        # 3. Alle Geräte aus der DB abrufen
        response = table.scan()
        items = response.get('Items', [])
        
        all_endpoints = []

        for record in items:
            # Erstelle das Device-Objekt
            device = AlexaDevice(record)
            
            # Hole den vollständigen Endpunkt-Payload (inkl. additionalAttributes & Capabilities)
            endpoint_data = device.get_discovery_payload()
            
            # Füge den Endpunkt zur Liste hinzu
            all_endpoints.append(endpoint_data)
            print(f"Gerät hinzugefügt: {device.friendly_name} [{device.endpoint_id}]")

        # 4. Die Liste der Endpunkte in die Response schreiben
        # Da wir die CamelCase-Struktur im Device haben, passt es direkt in den Payload
        adr.set_payload_endpoints(all_endpoints)

        # 5. Das Endergebnis drucken (Die komplette JSON-Struktur)
        full_response = adr.get()
        
        print("\n--- Vollständige Alexa Discovery Response ---")
        print(json.dumps(full_response, indent=2))

    except Exception as e:
        print(f"Fehler: {e}")

if __name__ == "__main__":
    test_full_discovery_response()
