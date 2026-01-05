# controllers/power_controller.py

import logging
from .alexa_controller import AlexaController

# Logger konfigurieren
logger = logging.getLogger(__name__)

class PowerController(AlexaController):
    namespace = "Alexa.PowerController"

    @staticmethod
    def get_capability(proactive=False, retrievable=True):
        return {
            "type": "AlexaInterface",
            "interface": "Alexa.PowerController",
            "version": "3",
            "properties": {
                "supported": [{"name": "powerState"}],
                "retrievable": retrievable,
                "proactivelyReported": proactive
            }
        }

    @staticmethod
    def get_properties(state_dict):
        # Wir erwarten in state_dict['power'] den Wert "ON" oder "OFF"
        value = state_dict.get('powerState', 'OFF')
        return [{
            "namespace": "Alexa.PowerController",
            "name": "powerState",
            "value": value
        }]

    @staticmethod
    def handle_directive(name, payload, current_state=None):
        logger.info(f"PowerController: Handling '{name}'")

        if name not in ("TurnOn", "TurnOff"):
            logger.warning(f"PowerController: Directive '{name}' not supported.")
            return {}

        value = "ON" if name == "TurnOn" else "OFF"

        return {
            "alexa": {"powerState": value},
            "openhab": value
        }

    @staticmethod
    def handle_update(update_dict):
        state = update_dict.get("state")
        if state in ["ON", "OFF"]:
            return {"powerState": state}
        return {}
