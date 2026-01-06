# test_discovery.py

import pytest
from lambda_function import lambda_handler  # Passe den Pfad zu deiner Lambda-Datei an


def test_discovery_laboratory_devices():
    """Ruft die Lambda auf und prüft alle Laboratory-Geräte."""

    # Ein typischer Alexa Discovery Request
    discovery_request = {
        "directive": {
            "header": {
                "namespace": "Alexa.Discovery",
                "name": "Discover",
                "payloadVersion": "3",
                "messageId": "123-456-789"
            },
            "payload": {
                "scope": {
                    "type": "BearerToken",
                    "token": "access-token-from-skill"
                }
            }
        }
    }

    # Lambda aufrufen
    response = lambda_handler(discovery_request, None)

    # Die Liste der Endpunkte aus der Antwort extrahieren
    endpoints = response["event"]["payload"]["endpoints"]

    lab_devices = [e for e in endpoints if "labor" in e["friendlyName"].lower()]

    print(f"\n[DEBUG] Gefundene Laboratory-Geräte: {len(lab_devices)}")

    # Validierung
    assert len(lab_devices) > 0, "Keine Laboratory-Geräte in der Discovery gefunden!"

    for device in lab_devices:
        print(f"Prüfe Gerät: {device['friendlyName']} ({device['endpointId']})")

        # Check: Hat jedes Lab-Gerät mindestens eine Capability?
        assert len(device["capabilities"]) > 0

        # Check: Ist die endpointId gesetzt?
        assert device["endpointId"] is not None