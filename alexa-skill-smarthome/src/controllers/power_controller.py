# controllers/power_controller.py

from .alexa_controller import AlexaController

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
        value = state_dict.get('power', 'OFF') 
        return [{
            "namespace": "Alexa.PowerController",
            "name": "powerState",
            "value": value
        }]

    @staticmethod
    def handle_directive(name, payload):
        # name ist "TurnOn" oder "TurnOff"
        value = "ON" if name == "TurnOn" else "OFF"
        return {"power": value}
