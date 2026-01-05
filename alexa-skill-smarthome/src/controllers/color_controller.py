# controllers/color_controller.py

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
    def handle_directive(name, payload, current_state=None):
        logger.info(f"ColorController: Handling '{name}'")

        if name == "SetColor":
            new_color = payload.get('color')

            # Validierung des Alexa-Payloads
            if not new_color or not all(k in new_color for k in ("hue", "saturation", "brightness")):
                logger.error(f"ColorController: Invalid color payload: {new_color}")
                return {}

            # 1. Alexa-Format (für DynamoDB)
            alexa_state = {"color": new_color}

            # 2. OpenHAB-Format (Konvertierung zu H,S,V String)
            # OpenHAB erwartet oft: "hue,saturation,brightness"
            # Alexa liefert Floats, OpenHAB bevorzugt oft gerundete Werte oder Floats als String
            h = new_color['hue']
            s = new_color['saturation'] * 100  # Alexa: 0.0-1.0 -> OpenHAB: 0-100
            b = new_color['brightness'] * 100  # Alexa: 0.0-1.0 -> OpenHAB: 0-100

            openhab_command = f"{h:.1f},{s:.1f},{b:.1f}"

            logger.info(f"ColorController: Alexa color {new_color} mapped to OpenHAB: {openhab_command}")

            return {
                "alexa": alexa_state,
                "openhab": openhab_command
            }

        logger.warning(f"ColorController: Directive '{name}' not supported.")
        return {}

    @staticmethod
    def handle_update(update_dict):
        state = update_dict.get("state")
        if not state:
            return {}

        try:
            # OpenHAB sendet HSB oft als String: "H,S,B" (z.B. "240.0,100.0,50.0")
            if isinstance(state, str) and "," in state:
                parts = state.split(",")
                if len(parts) == 3:
                    h = float(parts[0])
                    # OpenHAB nutzt 0-100 für S und B, Alexa nutzt 0.0-1.0
                    s = float(parts[1]) / 100.0
                    b = float(parts[2]) / 100.0

                    return {
                        "color": {
                            "hue": h,
                            "saturation": s,
                            "brightness": b
                        }
                    }
        except (ValueError, TypeError, IndexError) as e:
            logger.error(f"ColorController Update Error: {str(e)}")

        return {}