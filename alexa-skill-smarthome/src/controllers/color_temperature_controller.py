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
    def handle_directive(name, payload):
        logger.info(f"ColorTemperatureController: Handling directive '{name}' with payload: {payload}")

        # Standard-Fallback bei Fehlern: Warmweiß
        fallback_temp = 2700

        if name == "SetColorTemperature":
            temp_value = payload.get('colorTemperatureInKelvin')

            if temp_value is not None:
                logger.info(f"ColorTemperatureController: SetColorTemperature to {temp_value}K")
                return {"colorTemperatureInKelvin": int(temp_value)}
            else:
                logger.error("ColorTemperatureController: Missing temperature value in SetColorTemperature payload.")
                return {"colorTemperatureInKelvin": fallback_temp}

        elif name in ("IncreaseColorTemperature", "DecreaseColorTemperature"):
            # Diese Direktiven werden gesendet bei "Alexa, mach das Licht kühler/wärmer"
            # Da wir hier keinen direkten Zugriff auf den aktuellen State haben ohne DB-Lookup,
            # wird oft empfohlen, dies im übergeordneten Handler zu lösen oder hier einen
            # relativen Sprung (z.B. +/- 500K) zurückzugeben, falls dein System das kann.
            logger.warning(f"ColorTemperatureController: Relative change '{name}' requested but not implemented here.")
            return {}

        logger.warning(f"ColorTemperatureController: Directive '{name}' not supported.")
        return {}