# controllers/rollershutter_controller.py

from .alexa_controller import AlexaController


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
    def handle_directive(name, payload):
        # name ist "SetMode", payload['mode'] ist "Position.Up"
        if name == "SetMode":
            mode_value = payload["mode"].split(".")[-1]  # "Up", "Down", "Stopped"
            return {"mode": mode_value.upper()}
        return {}

    @staticmethod
    def handle_update(update_dict):
        # Hardware (OpenHAB) -> DB
        # Angenommen OpenHAB schickt: {"state": "OPEN"} oder {"state": "CLOSED"}
        oh_state = update_dict.get("state")
        if oh_state == "OPEN":
            return {"mode": "Position.Up"}
        elif oh_state == "CLOSED":
            return {"mode": "Position.Down"}
        elif oh_state == "MOVE":  # Nur ein Beispiel
            return {"mode": "Position.Stopped"}
        return {}
