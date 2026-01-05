# controllers/toggle_controller.py

import logging
from .alexa_controller import AlexaController

# Logger konfigurieren
logger = logging.getLogger(__name__)

class ToggleController(AlexaController):
    namespace = "Alexa.ToggleController"
    # Eine Instanz ist bei ToggleController PFLICHT
    instance = "Light.Backlight"

    @staticmethod
    def get_capability(proactive=False, retrievable=True):
        return {
            "type": "AlexaInterface",
            "interface": "Alexa.ToggleController",
            "version": "3",
            "instance": ToggleController.instance, # Instanz hier definieren
            "properties": {
                "supported": [{"name": "toggleState"}],
                "retrievable": retrievable,
                "proactivelyReported": proactive
            },
            "capabilityResources": {
                "friendlyNames": [
                    {"@type": "text", "value": {"text": "Hintergrundlicht", "locale": "de-DE"}}
                ]
            }
        }

    @staticmethod
    def get_properties(state_dict):
        # Wir speichern den State spezifisch für diese Instanz in der DB
        # Falls du mehrere Toggles hast, wäre der Key z.B. 'toggleState#Light.Backlight'
        value = state_dict.get('toggleState', 'OFF')
        return [{
            "namespace": "Alexa.ToggleController",
            "instance": ToggleController.instance, # Instanz auch hier zurückgeben
            "name": "toggleState",
            "value": value
        }]

    @staticmethod
    def handle_directive(name, payload, current_state=None):
        logger.info(f"ToggleController: Handling '{name}'")
        # Alexa sendet TurnOn oder TurnOff
        value = "ON" if name == "TurnOn" else "OFF"

        return {
            "alexa": {"toggleState": value},
            "openhab": value
        }

    @staticmethod
    def handle_update(update_dict):
        state = update_dict.get("state")
        if state in ["ON", "OFF"]:
            return {"toggleState": state}
        return {}
