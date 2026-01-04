import logging
from .alexa_controller import AlexaController

# Logger konfigurieren
logger = logging.getLogger(__name__)


class ColorController(AlexaController):
    namespace = "Alexa.ColorController"

    @staticmethod
    def get_capability(proactive=False, retrievable=True):
        return {
            "type": "AlexaInterface",
            "interface": "Alexa.ColorController",
            "version": "3",
            "properties": {
                "supported": [{"name": "color"}],
                "retrievable": retrievable,
                "proactivelyReported": proactive
            }
        }

    @staticmethod
    def get_properties(state_dict):
        # Fallback Werte (Schwarz / Aus)
        black = {"hue": 0.0, "saturation": 0.0, "brightness": 0.0}

        # Den Wert aus dem state_dict (DynamoDB Map) holen
        value = state_dict.get('color')
        logger.debug(f"ColorController: Raw value from state_dict: {value}")

        if not isinstance(value, dict):
            logger.warning(f"ColorController: Invalid data type for 'color': {type(value)}. Returning black.")
            value = black

        # Validierung der erforderlichen Keys
        required_keys = ("hue", "saturation", "brightness")
        if not all(k in value for k in required_keys):
            logger.error(f"ColorController: Missing keys in color dict: {value}. Returning black.")
            value = black

        # Konvertierung zu float für Alexa-Konformität
        try:
            formatted_value = {
                "hue": float(value.get("hue", 0.0)),
                "saturation": float(value.get("saturation", 0.0)),
                "brightness": float(value.get("brightness", 0.0))
            }
        except Exception as e:
            logger.error(f"ColorController: Error during float conversion: {str(e)}")
            formatted_value = black

        return [{
            "namespace": "Alexa.ColorController",
            "name": "color",
            "value": formatted_value
        }]

    @staticmethod
    def handle_directive(name, payload):
        logger.info(f"ColorController: Handling directive '{name}' with payload: {payload}")

        # Standard-Fallback bei Fehlern: Schwarz (Aus)
        fallback_color = {"hue": 0.0, "saturation": 0.0, "brightness": 0.0}

        if name == "SetColor":
            color_value = payload.get('color')

            if not color_value or not isinstance(color_value, dict):
                logger.error(f"ColorController: Received invalid 'color' payload in SetColor: {color_value}")
                return {"color": fallback_color}

            # Prüfung auf korrekte Struktur im Payload von Alexa
            if all(k in color_value for k in ("hue", "saturation", "brightness")):
                logger.info(f"ColorController: Successfully extracted color: {color_value}")
                return {"color": color_value}
            else:
                logger.error(f"ColorController: Incomplete color object in payload: {color_value}")
                return {"color": fallback_color}

        logger.warning(f"ColorController: Directive '{name}' not supported by this controller.")
        return {}