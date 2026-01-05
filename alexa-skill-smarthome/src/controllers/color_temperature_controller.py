# controllers/color_temperature_controller.py

import logging
from .alexa_controller import AlexaController

# Logger konfigurieren
logger = logging.getLogger(__name__)


class ColorTemperatureController(AlexaController):
    namespace = "Alexa.ColorTemperatureController"

    @staticmethod
    def get_capability(proactive=False, retrievable=True):
        return {
            "type": "AlexaInterface",
            "interface": "Alexa.ColorTemperatureController",
            "version": "3",
            "properties": {
                "supported": [{"name": "colorTemperatureInKelvin"}],
                "retrievable": retrievable,
                "proactivelyReported": proactive
            }
        }

    @staticmethod
    def get_properties(state_dict):
        # Fallback: Warmweiß (2700K)
        default_temp = 2700

        # Den Wert aus dem DynamoDB state_dict holen
        value = state_dict.get('colorTemperatureInKelvin')
        logger.debug(f"ColorTemperatureController: Raw value from state_dict: {value}")

        if value is None:
            logger.warning("ColorTemperatureController: No value found in state_dict. Using default 2700K.")
            value = default_temp

        try:
            # Alexa erwartet einen Integer für Kelvin
            formatted_value = int(value)
        except (ValueError, TypeError) as e:
            logger.error(f"ColorTemperatureController: Conversion error for value {value}: {str(e)}")
            formatted_value = default_temp

        return [{
            "namespace": "Alexa.ColorTemperatureController",
            "name": "colorTemperatureInKelvin",
            "value": formatted_value
        }]

    @staticmethod
    def handle_directive(name, payload, current_state=None):
        logger.info(f"ColorTemperatureController: Handling '{name}'")

        fallback_temp = 2700
        new_temp = None

        # --- Absolute Steuerung ---
        if name == "SetColorTemperature":
            # Wir nehmen den Wert nur an, wenn er wirklich im Payload ist
            new_temp = payload.get('colorTemperatureInKelvin')
            if new_temp is None:
                logger.error("ColorTemperatureController: No value in SetColorTemperature")
                return {}  # Abbruch ohne Aktion

        # --- Relative Steuerung ---
        elif name in ("IncreaseColorTemperature", "DecreaseColorTemperature"):
            # Aktuellen Wert ermitteln
            current_val = current_state.get('colorTemperatureInKelvin',
                                            fallback_temp) if current_state else fallback_temp

            # Delta berechnen
            delta = 500 if name == "IncreaseColorTemperature" else -500
            new_temp = int(current_val + delta)

            # Grenzen einhalten
            new_temp = max(1000, min(10000, new_temp))
            logger.info(f"ColorTemperature adjustment: {current_val}K -> {new_temp}K")

        # --- Ergebnis verarbeiten ---
        if new_temp is not None:
            return {
                "alexa": {"colorTemperatureInKelvin": int(new_temp)},
                "openhab": int(new_temp)  # Hier könntest du 1000000 / new_temp rechnen, falls du Mireds brauchst
            }

        logger.warning(f"ColorTemperatureController: Directive '{name}' not supported.")
        return {}

    # controllers/color_temperature_controller.py

    @staticmethod
    def handle_update(update_dict):
        state = update_dict.get("state")
        if state is None:
            return {}

        try:
            # OpenHAB liefert den Wert meist als Zahl (Kelvin)
            temp_kelvin = int(float(state))

            # Validierung: Ein sinnvoller Bereich für Kelvin (1000 - 10000)
            if 1000 <= temp_kelvin <= 10000:
                return {"colorTemperatureInKelvin": temp_kelvin}

            # Spezialfall: Falls dein OpenHAB Mireds sendet (oft Werte < 1000)
            # rechnen wir es für Alexa in Kelvin um: Kelvin = 1.000.000 / Mired
            elif 100 <= temp_kelvin < 1000:
                converted_kelvin = int(1000000 / temp_kelvin)
                return {"colorTemperatureInKelvin": converted_kelvin}

        except (ValueError, TypeError):
            pass

        return {}