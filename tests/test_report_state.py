import pytest
from index import lambda_handler


def test_sensorik_report_state():
    eid = "57f0e723-e6b0-460b-a087-997957d2aac7"  # Sensorik Labor

    event = {
        "directive": {
            "header": {"namespace": "Alexa", "name": "ReportState", "payloadVersion": "3", "messageId": "2"},
            "endpoint": {"endpointId": eid},
            "payload": {}
        }
    }

    response = lambda_handler(event, None)

    # Validierung der Struktur
    assert response["event"]["header"]["name"] == "StateReport"
    properties = response["context"]["properties"]

    # Wir suchen nach Temperatur und Feuchtigkeit in den Properties
    namespaces = [p["namespace"] for p in properties]
    assert "Alexa.TemperatureSensor" in namespaces
    assert "Alexa.HumiditySensor" in namespaces

    print(f"\n[ReportState] Sensorik Labor liefert {len(properties)} Werte.")