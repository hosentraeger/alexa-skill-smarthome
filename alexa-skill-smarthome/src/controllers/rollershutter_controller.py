# controllers/rollershutter_controller.py

import logging
from .alexa_controller import AlexaController

# Logger konfigurieren
logger = logging.getLogger(__name__)


class RollershutterController(AlexaController):
    namespace = "Alexa.ModeController"
    instance = "Blind.Position"

    @staticmethod
    def get_capability(proactive=False, retrievable=True):
        return {
            "capabilityResources": {
                "friendlyNames": [
                    {"@type": "asset", "value": {"assetId": "Alexa.Setting.Opening"}}
                ]
            },
            "configuration": {
                "ordered": False,
                "supportedModes": [
                    {
                        "value": "Position.Up",
                        "modeResources": {
                            "friendlyNames": [
                                {
                                    "@type": "asset",
                                    "value": {"assetId": "Alexa.Value.Open"},
                                }
                            ]
                        },
                    },
                    {
                        "value": "Position.Down",
                        "modeResources": {
                            "friendlyNames": [
                                {
                                    "@type": "asset",
                                    "value": {"assetId": "Alexa.Value.Close"},
                                }
                            ]
                        },
                    },
                    {
                        "value": "Position.Stopped",
                        "modeResources": {
                            "friendlyNames": [
                                {
                                    "@type": "text",
                                    "value": {"locale": "de-DE", "text": "Stopp"},
                                }
                            ]
                        },
                    },
                ],
            },
            "semantics": {
                "actionMappings": [
                    {
                        "@type": "ActionsToDirective",
                        "actions": [
                            "Alexa.Actions.Close",
                            "Alexa.Actions.Lower",  # Dies mappt "runter", "senken", "schließen"
                        ],
                        "directive": {
                            "name": "SetMode",
                            "payload": {"mode": "Position.Down"},
                        },
                    },
                    {
                        "@type": "ActionsToDirective",
                        "actions": [
                            "Alexa.Actions.Open",
                            "Alexa.Actions.Raise",  # Dies mappt "hoch", "heben", "öffnen"
                        ],
                        "directive": {
                            "name": "SetMode",
                            "payload": {"mode": "Position.Up"},
                        },
                    },
                ],
                "stateMappings": [
                    {
                        "@type": "StatesToValue",
                        "states": ["Alexa.States.Closed"],
                        "value": "Position.Down",
                    },
                    {
                        "@type": "StatesToValue",
                        "states": ["Alexa.States.Open"],
                        "value": "Position.Up",
                    },
                ],
            },
            "type": "AlexaInterface",
            "interface": "Alexa.ModeController",
            "instance": RollershutterController.instance,
            "version": "3",
            "properties": {
                "proactivelyReported": proactive,
                "retrievable": retrievable,
                "supported": [{"name": "mode"}],
            },
        }

    @staticmethod
    def get_properties(state_dict):
        # Wir erwarten in der DB Werte wie "Position.Up", "Position.Down" oder "Position.Stopped"
        # Falls in der DB nur "opened" steht, muss hier gemappt werden:
        value = state_dict.get("mode", "Position.Stopped")

        return [
            {
                "namespace": "Alexa.ModeController",
                "instance": RollershutterController.instance,
                "name": "mode",
                "value": value,
            }
        ]

    @staticmethod
    def handle_directive(name, payload, current_state=None):
        logger.info(f"Rollershutter: Handling '{name}'")

        if name == "SetMode":
            # 1. Wir behalten den VOLLEN Namen für die Datenbank/Alexa (Status-Reporting)
            # Alexa schickt z.B. "Position.Up"
            full_mode = payload.get("mode")

            # 2. Wir extrahieren den Befehl für OpenHAB
            # Wir mappen die Alexa-Werte auf die OpenHAB-Strings
            oh_command = "STOP"
            if "Up" in full_mode:
                oh_command = "UP"
            elif "Down" in full_mode:
                oh_command = "DOWN"
            elif "Stopped" in full_mode:
                oh_command = "STOP"

            return {
                "alexa": {"mode": full_mode},  # Speichert "Position.Up" in DynamoDB
                "openhab": oh_command  # Sendet "UP" via MQTT
            }

        logger.warning(f"Rollershutter: Directive '{name}' not supported.")
        return {}

    @staticmethod
    def handle_update(update_dict):
        oh_state = update_dict.get("state")  # z.B. "CLOSED", "OPEN" oder "MOVE"/"STOP"

        # Mapping von OpenHAB Status auf Alexa Mode-Werte
        if oh_state == "CLOSED":
            return {"mode": "Position.Down"}
        elif oh_state == "OPEN":
            return {"mode": "Position.Up"}
        elif oh_state in ["STOP", "MOVE", "UNDEF"]:
            # Wenn der Rolladen mitten im Lauf gestoppt wurde
            return {"mode": "Position.Stopped"}

        return {}
