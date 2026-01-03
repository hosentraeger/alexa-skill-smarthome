# controllers/brightness_controller.py

from .alexa_controller import AlexaController

class BrightnessController(AlexaController):
    namespace = "Alexa.BrightnessController"

    @staticmethod
    def get_capability(proactive=False, retrievable=True):
        return {
            "type": "AlexaInterface",
            "interface": "Alexa.BrightnessController",
            "version": "3",
            "properties": {
                "supported": [{"name": "brightness"}],
                "retrievable": retrievable,
                "proactivelyReported": proactive
            }
        }

    @staticmethod
    def get_properties(state_dict):
        # Wir erwarten in state_dict['brightness'] einen Wert zwischen 0 und 100.
        # Falls der Wert fehlt, setzen wir ihn standardmäßig auf 0.
        value = state_dict.get('brightness', 0)
        
        # Sicherstellen, dass der Wert ein Integer ist (falls er als String aus der DB kommt)
        try:
            value = int(value)
        except (ValueError, TypeError):
            value = 0

        return [{
            "namespace": "Alexa.BrightnessController",
            "name": "brightness",
            "value": value
        }]

    @staticmethod
    def handle_directive(name, payload):
        # RICHTUNG: ALEXA -> MQTT/DB
        if name == "SetBrightness":
            # Alexa schickt: {"brightness": 75}
            brightness_value = payload.get('brightness', 0)
            
            # Wir geben das Dict zurück, das MQTT und den internen State aktualisiert
            return {"brightness": brightness_value}
        
        elif name == "AdjustBrightness":
            # Optional: Alexa schickt ein Delta, z.B. {"brightnessDelta": -10}
            # Da wir im Controller aber keinen Zugriff auf den aktuellen DB-Stand haben,
            # überlassen wir die Berechnung meistens der Logik im AlexaDevice
            # oder wir ignorieren es, da Alexa oft selbst den neuen absoluten Wert berechnet.
            pass
            
        return {}