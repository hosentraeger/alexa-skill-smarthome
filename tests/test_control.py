import pytest
from unittest.mock import patch
from lambda_function import lambda_handler  # Passe den Pfad zu deiner Lambda-Datei an


@pytest.mark.parametrize("name, eid, namespace, command, value", [
    ("Schalter Labor", "d78a4851-8615-44f2-a944-21977d272952", "Alexa.PowerController", "TurnOn", "ON"),
    ("RGB-Licht Labor", "9c650264-931a-47ef-a025-4076ace727fe", "Alexa.ColorController", "SetColor",
     {"hue": 0, "saturation": 1, "brightness": 1})
])
def test_control_mqtt_publish(name, eid, namespace, command, value):
    # Wir mocken den MQTT-Client (Passe den Pfad zu deinem MQTT-Controller an!)
    with patch("controllers.alexa_controller.mqtt.Client.publish") as mock_publish:
        control_event = {
            "directive": {
                "header": {"namespace": namespace, "name": command, "payloadVersion": "3", "messageId": "1"},
                "endpoint": {"endpointId": eid},
                "payload": value if isinstance(value, dict) else {}
            }
        }

        response = lambda_handler(control_event, None)

        # Prüfung 1: Hat die Lambda Erfolg an Alexa gemeldet?
        assert response["event"]["header"]["name"] == "Response"

        # Prüfung 2: Wurde die MQTT-Nachricht abgesetzt?
        assert mock_publish.called
        args, kwargs = mock_publish.call_args
        print(f"\n[MQTT Check] {name} sendet an Topic: {args[0]}")