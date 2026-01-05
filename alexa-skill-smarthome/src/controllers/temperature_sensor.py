# controllers/temperature_sensor.py

from .alexa_controller import AlexaController

class TemperatureSensor(AlexaController):
    namespace = "Alexa.TemperatureSensor"

    @staticmethod
    def get_capability(proactive=True, retrievable=True):
        return {
            "type": "AlexaInterface",
            "interface": "Alexa.TemperatureSensor",
            "version": "3",
            "properties": {
                "supported": [{"name": "temperature"}],
                # Sensoren sind fast immer retrievable (Zustand abfragbar)
                "retrievable": retrievable,
                "proactivelyReported": proactive
            }
        }

    @staticmethod
    def get_properties(state_dict):
        # Alexa erwartet bei Temperatur ein Objekt mit 'value' und 'scale'
        # Wir nutzen -273.15 (absoluter Nullpunkt) als sicheren Fehler-Default
        raw_value = state_dict.get('temperature', -273.15)
        
        try:
            # Sicherstellen, dass es eine Fließkommazahl ist
            temp_value = float(raw_value)
        except (ValueError, TypeError):
            temp_value = -273.15

        return [{
            "namespace": "Alexa.TemperatureSensor",
            "name": "temperature",
            "value": {
                "value": temp_value,
                "scale": "CELSIUS"  # Alexa unterstützt CELSIUS, FAHRENHEIT, KELVIN
            }
        }]

    @staticmethod
    def handle_directive(name, payload, current_state=None):
        # Sensoren empfangen normalerweise keine Direktiven von Alexa,
        # aber das Interface muss für den Discovery/Handler-Loop existieren.
        return {}

    @staticmethod
    def handle_update(update_dict):
        state = update_dict.get("state")
        try:
            # OpenHAB liefert oft Strings, Alexa will Floats
            return {"temperature": float(state)}
        except (ValueError, TypeError):
            return {}
