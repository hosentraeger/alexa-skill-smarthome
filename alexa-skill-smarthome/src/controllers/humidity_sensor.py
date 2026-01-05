# controllers/humidity_sensor.py

from .alexa_controller import AlexaController


class HumiditySensor(AlexaController):
    namespace = "Alexa.HumiditySensor"

    @staticmethod
    def get_capability(proactive=True, retrievable=True):
        return {
            "type": "AlexaInterface",
            "interface": "Alexa.HumiditySensor",
            "version": "3",
            "properties": {
                "supported": [{"name": "relativeHumidity"}],
                "retrievable": retrievable,
                "proactivelyReported": proactive
            }
        }

    @staticmethod
    def get_properties(state_dict):
        raw_value = state_dict.get('relativeHumidity', 0.0)

        try:
            humidity_value = float(raw_value)
        except (ValueError, TypeError):
            humidity_value = 0.0

        return [{
            "namespace": "Alexa.HumiditySensor",
            "name": "relativeHumidity",
            "value": {
                "value": humidity_value
            }
        }]

    @staticmethod
    def handle_directive(name, payload, current_state=None):
        # MotionSensoren empfangen normalerweise keine Direktiven von Alexa,
        # aber das Interface muss für den Discovery/Handler-Loop existieren.
        return {}

    @staticmethod
    def handle_update(update_dict):
        state = update_dict.get("state")
        try:
            # OpenHAB liefert oft Strings, Alexa will Floats
            return {"relativeHumidity": float(state)}
        except (ValueError, TypeError):
            return {}
