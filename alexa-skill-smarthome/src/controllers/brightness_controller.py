# controllers/brightness_controller.py

import logging
from .alexa_controller import AlexaController

logger = logging.getLogger(__name__)


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
        # Alexa erwartet einen Integer zwischen 0 und 100
        value = state_dict.get('brightness', 0)
        try:
            formatted_value = int(value)
        except (ValueError, TypeError):
            formatted_value = 0

        return [{
            "namespace": "Alexa.BrightnessController",
            "name": "brightness",
            "value": formatted_value
        }]


    @staticmethod
    def handle_directive(name, payload, current_state=None):
        logger.info(f"BrightnessController: Handling directive '{name}' with payload: {payload}")
        new_brightness = None

        # 1. Absolute Steuerung
        if name == "SetBrightness":
            new_brightness = int(payload.get('brightness', 0))

        # 2. Relative Steuerung (Delta)
        elif name == "AdjustBrightness":
            current_val = current_state.get('brightness', 50) if current_state else 50
            delta = payload.get('brightnessDelta', 0)
            new_brightness = max(0, min(100, int(current_val + delta)))
            logger.info(f"Brightness adjustment: {current_val}% -> {new_brightness}%")

        else:
            pass

        if new_brightness is not None:
            return {
                "alexa": {"brightness": new_brightness},  # Für DynamoDB
                "openhab": new_brightness  # Für MQTT/OpenHAB
            }

        return {}

        # controllers/brightness_controller.py

    @staticmethod
    def handle_update(update_dict):
        state = update_dict.get("state")
        if state is None:
            return {}

        try:
            # 1. Fall: Numerischer Wert (Helligkeit 0-100)
            # Wir versuchen, den Status in eine Zahl zu wandeln
            brightness_val = int(float(state))

            # Validierung: Nur Werte zwischen 0 und 100 sind gültig
            if 0 <= brightness_val <= 100:
                return {"brightness": brightness_val}
        except (ValueError, TypeError):
            # 2. Fall: String-Wert (z.B. "OFF" -> Brightness 0)
            # Manche Systeme senden "OFF" statt "0" über den Dimmer-Kanal
            if str(state).upper() == "OFF":
                return {"brightness": 0}
            elif str(state).upper() == "ON":
                # "ON" ist schwer zu mappen, da wir die letzte Helligkeit nicht kennen.
                # Meistens lassen wir das den PowerController regeln.
                pass

        return {}